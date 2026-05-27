from __future__ import annotations

"""
vision_extractor.py — fixes applied
======================================
BUG 1 (LLM sees a bbox-highlighted image): The original code called
render_highlighted_bboxes() to draw coloured boxes on the document image,
then sent THAT image to the LLM.  Coloured overlay boxes obscure text and
confuse the vision model, causing it to misread numbers/names under the
boxes.  Fix: always send the clean preprocessed image to the LLM.

BUG 2 (weak, ambiguous prompt): The prompt listed field names as a
comma-separated string and appended a wall of OCR blocks in a numbered
format.  The LLM couldn't reliably map OCR block indices back to schema
field names, often returning either the raw block list as JSON or an empty
object.  Fix: write a clear prompt with (a) an explicit JSON output
template showing every required field, (b) the OCR text as a clean
paragraph (not numbered blocks), and (c) strong negative instructions.

BUG 3 (repair fallback uses text-only call): When the vision call
returned < 4 fields the code called _call_text() (no image).  The text-
only model has no vision capability so it can't recover fields that OCR
missed.  Fix: the repair call also sends the image.

BUG 4 (date/currency normalisation after stripping confidence wrappers):
The normalisation loop treated every value as a plain scalar, but the LLM
often returns {"value": "...", "confidence": "high"} objects.  The code
correctly unwraps these in _normalize_extract in llm_client but then
vision_extractor re-wraps them after running validators, producing
double-nested structures.  Fix: unwrap before normalising, stay flat.
"""

# from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR
from backend.services.helpers import read_json_file, file_to_base64
from backend.services.llm_client import get_llm_client, _extract_json
from backend.services.validators import normalize_date, normalize_currency

logger = logging.getLogger(__name__)

SCHEMA_DIR = BASE_DIR / "backend" / "extraction_schemas"


def load_schema(doc_type: str) -> dict:
    schema_path = SCHEMA_DIR / f"{doc_type}.json"
    if schema_path.exists():
        return read_json_file(schema_path)
    return {"doc_type": doc_type, "fields": [], "prompt_hint": ""}


def _build_output_template(fields: list[dict]) -> str:
    """Build a concrete JSON template so the LLM knows exactly what shape to return."""
    template: dict[str, Any] = {}
    for field in fields:
        name = field.get("name")
        if not name:
            continue
        ftype = field.get("type", "string")
        if ftype == "table":
            cols = field.get("columns", ["col1", "col2"])
            template[name] = [{c: "..." for c in cols}]
        elif ftype in ("number", "currency"):
            template[name] = 0.0
        elif ftype == "boolean":
            template[name] = False
        else:
            template[name] = "..."
    return json.dumps(template, indent=2)


def _build_extraction_prompt(doc_type: str, schema: dict, ocr_text: str) -> str:
    fields = schema.get("fields", [])
    required = [f["name"] for f in fields if f.get("required") and f.get("name")]
    output_template = _build_output_template(fields)

    field_descriptions = []
    for f in fields:
        name = f.get("name", "")
        ftype = f.get("type", "string")
        req = " (REQUIRED)" if f.get("required") else ""
        desc = f.get("description", "")
        if ftype == "table":
            cols = ", ".join(f.get("columns", []))
            field_descriptions.append(f"  - {name}{req}: array of objects with columns [{cols}]")
        else:
            field_descriptions.append(f"  - {name}{req} ({ftype}){': ' + desc if desc else ''}")

    field_block = "\n".join(field_descriptions) if field_descriptions else "  (generic document fields)"

    prompt = f"""You are a precise document data extraction engine.

DOCUMENT TYPE: {doc_type}

YOUR TASK
Extract every field listed below from the document image. Use the image as the PRIMARY source of truth. Use the OCR text below only to help locate text regions — never trust OCR blindly for numbers, dates, or names; verify against the image.

FIELDS TO EXTRACT
{field_block}

OCR TEXT (may contain errors — verify against image):
\"\"\"
{ocr_text.strip() if ocr_text.strip() else "(no OCR text available)"}
\"\"\"

OUTPUT FORMAT
Return ONLY a JSON object matching this exact structure. No markdown, no explanation, no code fences:
{output_template}

RULES
- Use null for any field not visible in the document (do NOT invent values).
- Required fields ({', '.join(required) if required else 'none'}): make maximum effort; return null only if truly absent.
- Currency values: numeric only, no symbols (e.g. 1234.56 not "$1,234.56").
- Dates: ISO format YYYY-MM-DD where possible.
- For table/line_items fields: return an array of objects, one per row.
- The first character of your response MUST be {{ and the last MUST be }}.
"""
    return prompt


def extract_with_schema(payload: dict) -> dict:
    image_path = payload.get("image_path") or payload.get("processed_path")
    doc_type = payload.get("document_type") or payload.get("doc_type") or "form"
    ocr_text = payload.get("ocr_text") or ""

    # ── Always use the CLEAN preprocessed image, never the bbox overlay ──────
    # (Bug 1 fix: the original sent an overlay-annotated image to the LLM.)
    image_base64 = ""
    if image_path:
        try:
            image_base64 = file_to_base64(image_path)
        except Exception:
            logger.warning("Could not base64-encode image at %s", image_path)

    schema = load_schema(doc_type)
    schema_fields = [
        field.get("name")
        for field in schema.get("fields", [])
        if isinstance(field, dict) and field.get("name")
    ]

    # ── Primary extraction call ──────────────────────────────────────────────
    prompt = _build_extraction_prompt(doc_type, schema, ocr_text)
    data: dict[str, Any] = {}
    try:
        raw_text = get_llm_client()._call(prompt=prompt, image_base64=image_base64)
        data = _extract_json(raw_text)
        if not isinstance(data, dict):
            data = {}
        # If the LLM wrapped everything under a "fields" key, unwrap it.
        if set(data.keys()) <= {"fields", "summary", "entities", "tables"}:
            data = data.get("fields") or data
    except Exception:
        logger.exception("Vision LLM primary call failed")
        data = {}

    # ── Repair call if fewer than half the expected fields came back ─────────
    # (Bug 3 fix: repair also sends the image so vision can fill what OCR missed.)
    min_fields = max(2, len(schema_fields) // 2)
    if len([v for v in data.values() if v is not None]) < min_fields and schema_fields:
        repair_prompt = _build_extraction_prompt(doc_type, schema, ocr_text)
        repair_prompt += (
            "\n\nPREVIOUS ATTEMPT returned too few fields. "
            "Look more carefully at the image. Fill every field you can see."
        )
        try:
            repair_raw = get_llm_client()._call(prompt=repair_prompt, image_base64=image_base64)
            repair_data = _extract_json(repair_raw)
            if isinstance(repair_data, dict) and len(repair_data) >= min_fields:
                # Merge: repair fills missing slots, original wins for fields it already has.
                for k, v in repair_data.items():
                    if k not in data or data[k] is None:
                        data[k] = v
        except Exception:
            logger.exception("Vision LLM repair call failed")

    # ── Fallback: populate schema fields with null so downstream code never
    #    receives a missing key.
    if not data:
        data = {name: None for name in schema_fields}

    # ── Normalise values (dates, currencies) ────────────────────────────────
    # (Bug 4 fix: unwrap {"value":…, "confidence":…} objects before normalising
    #  so we never produce double-nested structures.)
    normalized: dict[str, Any] = {}
    for field_name, raw_value in data.items():
        # Unwrap LLM confidence objects.
        if isinstance(raw_value, dict) and "value" in raw_value:
            value = raw_value.get("value")
        else:
            value = raw_value

        if isinstance(value, str):
            if "date" in field_name or field_name.endswith("_date"):
                value = normalize_date(value) or value
            if field_name in ("total", "subtotal", "tax", "amount", "price", "unit_price"):
                normed = normalize_currency(value)
                if normed is not None:
                    value = normed

        normalized[field_name] = value

    return normalized