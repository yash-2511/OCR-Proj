from __future__ import annotations

import json
from typing import Any

from backend.services.helpers import confidence_from_score, normalize_bbox


def _bbox_from_ocr(value: str | None, ocr_items: list[dict[str, Any]]) -> list[int] | None:
    if not value:
        return None
    normalized_value = str(value).strip().lower()
    for item in ocr_items:
        text = str(item.get("text", "")).strip().lower()
        if not text:
            continue
        if normalized_value in text or text in normalized_value:
            bbox = item.get("bbox") or {}
            norm = normalize_bbox(bbox)
            if norm:
                return norm
            # fallback
            if isinstance(bbox, list) and len(bbox) == 4:
                return [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            if isinstance(bbox, dict):
                x = int(bbox.get("x", 0))
                y = int(bbox.get("y", 0))
                w = int(bbox.get("w", 0))
                h = int(bbox.get("h", 0))
                return [x, y, x + w, y + h]
    return None


def normalize_extraction_results(extracted: dict[str, Any], ocr_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for field_name, payload in extracted.items():
        if field_name.startswith("_"):
            continue
        value = payload.get("value") if isinstance(payload, dict) else payload
        confidence = payload.get("confidence") if isinstance(payload, dict) else 0.5
        if isinstance(value, dict) and "value" in value:
            confidence = value.get("confidence", confidence)
            value = value.get("value")
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False)
        bbox = _bbox_from_ocr(value, ocr_items) if isinstance(value, str) else None
        results.append(
            {
                "field_name": field_name,
                "field_value": value,
                "confidence": confidence if isinstance(confidence, (int, float)) else confidence_from_score(0.35),
                "confidence_score": float(confidence) if isinstance(confidence, (int, float)) else 0.35,
                "bbox": bbox,
            }
        )
    return results


def _parse_number(value: str) -> float | None:
    if value is None:
        return None
    try:
        s = str(value)
        # remove currency symbols and common OCR noise (commas, non-digits except dot and minus)
        s = s.replace("$", "").replace("€", "").replace("£", "")
        s = s.replace(",", "")
        # replace common OCR misreads (O -> 0, Q -> 0)
        s = s.replace("O", "0").replace("Q", "0")
        # keep digits, dot, minus
        import re

        m = re.search(r"-?[0-9]+(?:\.[0-9]+)?", s)
        if not m:
            return None
        return float(m.group(0))
    except Exception:
        return None


def cast_and_validate_numbers(extraction: dict[str, Any], doc_type: str) -> dict[str, Any]:
    """
    Cast numeric fields to floats and perform basic math validation for invoices/receipts.
    Mutates the extraction dict and returns it with an added 'validation' key.
    """
    validation = extraction.get("validation") or {}
    validation.setdefault("cast_failures", [])
    validation.setdefault("line_items_sum_mismatch", False)
    validation.setdefault("total_mismatch", False)

    def _get_field_val(name: str):
        v = extraction.get(name)
        if isinstance(v, dict):
            return v.get("value")
        return v

    # Only run for invoices/receipts
    if doc_type in ("invoice", "receipt"):
        # Cast subtotal, tax, total
        for field in ("subtotal", "tax", "total"):
            raw = _get_field_val(field)
            if raw is None:
                continue
            num = _parse_number(raw)
            if num is None:
                validation["cast_failures"].append(field)
                # set field to null
                if isinstance(extraction.get(field), dict):
                    extraction[field]["value"] = None
                else:
                    extraction[field] = None
            else:
                if isinstance(extraction.get(field), dict):
                    extraction[field]["value"] = num
                else:
                    extraction[field] = num

        # Cast line_items amounts
        line_items = _get_field_val("line_items")
        sum_amounts = 0.0
        line_item_cast_failures = []
        if line_items:
            # If line_items is a JSON string, attempt parse
            import json

            items = line_items
            if isinstance(line_items, str):
                try:
                    items = json.loads(line_items)
                except Exception:
                    items = None
            if isinstance(items, list):
                for idx, row in enumerate(items):
                    # expect dict with amount, quantity, unit_price
                    if not isinstance(row, dict):
                        continue
                    amount_raw = row.get("amount") or row.get("total") or row.get("price")
                    qty_raw = row.get("quantity") or row.get("qty")
                    unit_raw = row.get("unit_price") or row.get("unitPrice") or row.get("rate")
                    amount = _parse_number(amount_raw) if amount_raw is not None else None
                    qty = _parse_number(qty_raw) if qty_raw is not None else None
                    unit = _parse_number(unit_raw) if unit_raw is not None else None
                    if amount is None:
                        line_item_cast_failures.append(f"line_items[{idx}].amount")
                    else:
                        sum_amounts += amount
                    # replace values in the items structure
                    if amount is not None:
                        row["amount"] = amount
                    else:
                        row["amount"] = None
                    if qty is not None:
                        row["quantity"] = qty
                    else:
                        row["quantity"] = None
                    if unit is not None:
                        row["unit_price"] = unit
                    else:
                        row["unit_price"] = None
                # write back normalized line_items
                if isinstance(extraction.get("line_items"), dict):
                    extraction["line_items"]["value"] = items
                else:
                    extraction["line_items"] = items

        if line_item_cast_failures:
            validation["cast_failures"].extend(line_item_cast_failures)

        # Compare sums
        subtotal = _get_field_val("subtotal")
        tax = _get_field_val("tax")
        total = _get_field_val("total")
        try:
            subtotal_num = float(subtotal) if subtotal is not None else None
        except Exception:
            subtotal_num = None
        try:
            tax_num = float(tax) if tax is not None else 0.0
        except Exception:
            tax_num = None
        try:
            total_num = float(total) if total is not None else None
        except Exception:
            total_num = None

        # line items sum vs subtotal
        if sum_amounts and subtotal_num is not None:
            if abs(sum_amounts - subtotal_num) > 0.01:
                validation["line_items_sum_mismatch"] = True

        # subtotal + tax vs total
        if subtotal_num is not None and tax_num is not None and total_num is not None:
            if abs((subtotal_num + tax_num) - total_num) > 0.01:
                validation["total_mismatch"] = True
                # require human review
                extraction["requires_review"] = True

    extraction["validation"] = validation
    return extraction


def ensure_field_values(fields: dict[str, Any]) -> dict[str, Any]:
    """Ensure every field dict has a 'value' key by copying from 'raw_ocr_text' when missing."""
    if not isinstance(fields, dict):
        return fields
    for field_name, field_data in list(fields.items()):
        if isinstance(field_data, dict):
            if "value" not in field_data and "raw_ocr_text" in field_data and field_data.get("raw_ocr_text") is not None:
                field_data["value"] = field_data.get("raw_ocr_text")
                fields[field_name] = field_data
    return fields


REQUIRED_FIELDS = {
    "invoice": ["vendor", "invoice_number", "date", "total"],
    "receipt": ["merchant", "date", "total"],
    "business_card": ["name"],
    "id_card": ["full_name", "id_number"],
    "contract": ["parties", "effective_date"],
}


def _heal_from_ocr(field_name: str, ocr_result: dict[str, Any]) -> dict[str, Any] | None:
    import re
    PATTERNS = {
        "date": r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b",
        "total": r"\b(?:total|amount due|balance due)[:\s]*[\$€£]?[\d,]+\.?\d*",
        # tighter invoice pattern requiring a separator like - or /
        "invoice_number": r"\b([A-Z]{2,6}[-/]\d+[-/]?\d*)\b",
        "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"(?:\+?\d[\d\s\-\(\)]{7,15}\d)",
    }

    pattern = PATTERNS.get(field_name)
    if not pattern:
        return None

    # try higher-confidence blocks first
    sorted_blocks = sorted(ocr_result.get("words", []), key=lambda b: b.get("confidence", 0.0), reverse=True)

    for block in sorted_blocks:
        # position filter: skip header/title area
        bbox = block.get("bbox") or []
        try:
            y_top = int(bbox[1])
        except Exception:
            y_top = 0
        if y_top < 60:
            continue
        match = re.search(pattern, block.get("text", ""), re.IGNORECASE)
        if match:
            return {
                "value": match.group().strip(),
                "raw_ocr_text": block.get("text"),
                "bbox": block.get("bbox"),
                "confidence": "low",
                "source": "ocr_heuristic",
            }
    return None


def validate_and_heal(extraction: dict[str, Any], ocr_result: dict[str, Any], doc_type: str) -> dict[str, Any]:
    """
    After extraction and numeric validation, attempt to heal missing required fields
    using OCR heuristics. Modifies extraction in place and returns it.
    """
    required = REQUIRED_FIELDS.get(doc_type, [])
    fields = extraction if isinstance(extraction, dict) else {}
    missing = []

    for field_name in required:
        field = fields.get(field_name)
        value = field.get("value") if isinstance(field, dict) else field
        if value is None:
            healed = _heal_from_ocr(field_name, ocr_result)
            if healed:
                fields[field_name] = healed
            else:
                missing.append(field_name)

    validation = extraction.get("validation") or {}
    validation["missing_fields"] = missing
    extraction["validation"] = validation
    extraction["requires_review"] = len(missing) > 0 or extraction.get("requires_review", False)
    return extraction
