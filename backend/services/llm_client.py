from __future__ import annotations

"""
llm_client.py — fixes applied
================================
BUG 1 (weak extraction prompt): The extract() method built a prompt that
listed field names as "- fieldname (type)" bullets but never showed the
LLM what the output JSON should look like.  For invoice line_items in
particular, the LLM had no idea the value should be an array of objects
with specific column keys — it often returned a flat string or skipped the
field entirely.  Fix: inject a concrete JSON output template.

BUG 2 (max_tokens=4096 for Anthropic but 2048 in _call_anthropic): A
long invoice with 20 line items easily exceeds 2048 output tokens.
Fix: raise Anthropic max_tokens to 4096.

BUG 3 (repair call in extract() uses _call_text — no image): When the
primary vision call failed, the fallback called _call_text() which sends
no image.  A text-only model cannot recover fields that OCR missed or
misread.  Fix: repair also sends the image.

BUG 4 (image always encoded as image/png regardless of original format):
Sending a JPEG image with media_type=image/png causes some providers
(Anthropic in particular) to reject the request or produce garbage output.
Fix: detect the actual format from the base64 header bytes.
"""

# from __future__ import annotations

import json
import importlib
import os
import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from backend.config import Config
from backend.services.helpers import confidence_from_score, safe_json_loads


DOC_TYPES = [
    "invoice",
    "receipt",
    "business_card",
    "form",
    "id_card",
    "contract",
    "report",
    "handwritten",
    "whiteboard",
    "table",
]


OPENROUTER_MODEL_ALIASES = {
    "llama-3.2-11b-vision-instruct:free": "meta-llama/llama-3.2-11b-vision-instruct:free",
}

GROQ_MODEL_ALIASES = {
    "llama-4-scout-17b-16e-instruct": "meta-llama/llama-4-scout-17b-16e-instruct",
}


def _extract_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                return {}
            return safe_json_loads(match.group(0), default={}) or {}


def _detect_image_media_type(image_base64: str) -> str:
    """Detect image format from the first few decoded bytes rather than
    blindly using image/png for everything."""
    try:
        import base64
        header = base64.b64decode(image_base64[:16])
        if header[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if header[:4] == b"\x89PNG":
            return "image/png"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
    except Exception:
        pass
    return "image/png"


def _resolve_openrouter_model(model: str | None) -> str | None:
    if not model:
        return model
    return OPENROUTER_MODEL_ALIASES.get(model.strip(), model.strip())


def _resolve_groq_model(model: str | None) -> str | None:
    if not model:
        return model
    return GROQ_MODEL_ALIASES.get(model.strip(), model.strip())


def _build_output_template(fields: list[dict]) -> str:
    """Return a concrete JSON object template so the LLM knows the exact
    required output shape."""
    template: dict[str, Any] = {}
    for f in fields:
        name = f.get("name")
        if not name:
            continue
        ftype = f.get("type", "string")
        if ftype == "table":
            cols = f.get("columns", ["col1", "col2"])
            template[name] = [{c: "..." for c in cols}]
        elif ftype in ("number", "currency"):
            template[name] = 0.0
        elif ftype == "boolean":
            template[name] = False
        else:
            template[name] = "..."
    return json.dumps(template, indent=2)


@dataclass
class LLMClient:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.provider = (self.provider or Config.LLM_PROVIDER).lower()
        self.model = self.model or Config.LLM_MODEL
        if self.provider == "openrouter":
            self.model = _resolve_openrouter_model(self.model)
        if self.provider == "groq":
            self.model = _resolve_groq_model(self.model)
            self.api_key = self.api_key or Config.GROQ_API_KEY or Config.LLM_API_KEY
            self.base_url = self.base_url or Config.GROQ_BASE_URL
        else:
            self.api_key = self.api_key or Config.HF_TOKEN or Config.LLM_API_KEY
            self.base_url = self.base_url or Config.OPENROUTER_BASE_URL
        self.hf_endpoint_url = Config.HF_ENDPOINT_URL

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        image_base64: str,
        ocr_text: str = "",
        document_type_hint: str | None = None,
        layout_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prompt = (
            "Classify this document into exactly one of these categories: "
            + ", ".join(DOC_TYPES)
            + '\nReturn only JSON: {"doc_type":"<type>", "confidence":0.0}'
        )
        if document_type_hint:
            prompt += f"\nPreferred type hint: {document_type_hint}"
        if ocr_text.strip():
            prompt += f"\n\nOCR TEXT:\n{ocr_text.strip()}"
        try:
            payload = self._call(prompt=prompt, image_base64=image_base64)
            data = _extract_json(payload)
            doc_type = data.get("doc_type") if data.get("doc_type") in DOC_TYPES else "form"
            confidence = float(data.get("confidence", 0.35) or 0.35)
            return {"doc_type": doc_type, "confidence": max(0.0, min(1.0, confidence))}
        except Exception:
            return {"doc_type": "form", "confidence": 0.35}

    def extract(
        self,
        image_base64: str,
        schema: dict,
        doc_type: str,
        ocr_text: str = "",
        layout_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields = schema.get("fields", []) if isinstance(schema, dict) else []
        output_template = _build_output_template(fields)

        field_lines = []
        for field in fields:
            name = field.get("name", "")
            ftype = field.get("type", "string")
            req = " (REQUIRED)" if field.get("required") else ""
            if ftype == "table" and field.get("columns"):
                field_lines.append(
                    f"  - {name}{req}: array of objects, columns: {', '.join(field['columns'])}"
                )
            else:
                field_lines.append(f"  - {name}{req} ({ftype})")

        required_names = [f["name"] for f in fields if f.get("required") and f.get("name")]

        prompt = (
            f"You are a precise document data extraction engine.\n"
            f"Document type: {doc_type}\n\n"
            f"OCR text (may contain errors — verify against the image):\n"
            f'"""\n{ocr_text.strip() or "(none)"}\n"""\n\n'
            f"Fields to extract:\n"
            + "\n".join(field_lines)
            + f"\n\nRequired fields: {', '.join(required_names) or 'none'}"
            f"\n\nReturn ONLY a JSON object with this exact structure (no markdown, no explanation):\n"
            f"{output_template}\n\n"
            f"Rules:\n"
            f"- null for any field not found (do NOT invent values)\n"
            f"- Currency: numbers only, no symbols\n"
            f"- Dates: YYYY-MM-DD\n"
            f"- First char must be {{ last char must be }}"
        )

        try:
            payload = self._call(prompt=prompt, image_base64=image_base64)
            data = _extract_json(payload)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        # Repair: retry with image if fewer than half the fields came back.
        min_fields = max(2, len(fields) // 2)
        if len([v for v in data.values() if v is not None]) < min_fields:
            repair_prompt = prompt + (
                "\n\nPREVIOUS ATTEMPT returned too few fields. "
                "Look more carefully. Fill every visible field."
            )
            try:
                repair_raw = self._call(prompt=repair_prompt, image_base64=image_base64)
                repair_data = _extract_json(repair_raw)
                if isinstance(repair_data, dict):
                    for k, v in repair_data.items():
                        if k not in data or data[k] is None:
                            data[k] = v
            except Exception:
                pass

        if not data:
            return self._fallback_extract(fields)

        return self._normalize_extract(data, fields)

    def summarize(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        prompt = "\n".join([
            "You are an intelligent document analyst.",
            "Use the image as the PRIMARY source. OCR text may have errors.",
            "Identify the document type. Summarise in one short paragraph.",
            "Return ONLY valid JSON with no markdown:",
            '{"summary":"...","highlights":["..."],"document_type":"...","sections":[{"title":"...","value":"..."}]}',
            "",
            "Document context:",
            json.dumps(context, ensure_ascii=False, indent=2),
            "",
            "OCR text:",
            text or "",
        ])
        try:
            payload = self._call_text(prompt)
            data = _extract_json(payload)
            summary = str(data.get("summary") or "").strip()
            highlights = [str(h).strip() for h in (data.get("highlights") or []) if str(h).strip()]
            document_type = str(data.get("document_type") or "").strip()
            sections = [
                item for item in (data.get("sections") or [])
                if isinstance(item, dict)
                and str(item.get("title") or "").strip()
                and str(item.get("value") or "").strip()
            ]
            if not summary:
                raise ValueError("Empty summary")
            return {
                "summary": summary,
                "highlights": highlights[:5],
                "document_type": document_type,
                "sections": sections[:6],
            }
        except Exception:
            return self._fallback_summary(text, context)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _normalize_extract(self, data: dict, fields: list[dict]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in fields:
            name = field.get("name")
            if not name:
                continue
            raw = data.get(name)
            if isinstance(raw, dict) and {"value", "confidence"}.issubset(raw.keys()):
                value = raw.get("value")
                confidence = raw.get("confidence") or "low"
            else:
                value = raw
                confidence = data.get(f"{name}_confidence") or "low"
            normalized[name] = {"value": value, "confidence": confidence}
        # Carry through any extra keys the LLM returned.
        for key, value in data.items():
            if key.endswith("_confidence") or key in normalized:
                continue
            if isinstance(value, dict) and {"value", "confidence"}.issubset(value.keys()):
                normalized[key] = value
            else:
                normalized[key] = {"value": value, "confidence": "low"}
        return normalized

    def _fallback_extract(self, fields: list[dict]) -> dict[str, Any]:
        return {
            field.get("name"): {"value": None, "confidence": "low"}
            for field in fields
            if field.get("name")
        }

    # ── Provider dispatch ─────────────────────────────────────────────────────

    def _call(self, prompt: str, image_base64: str) -> str:
        if self.provider in ("openai", "openrouter", "groq"):
            return self._call_openai_compatible(prompt, image_base64)
        if self.provider == "huggingface":
            return self._call_huggingface(prompt, image_base64)
        if self.provider == "gemini":
            return self._call_gemini(prompt, image_base64)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, image_base64)
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _call_text(self, prompt: str) -> str:
        if self.provider in ("openai", "openrouter", "groq"):
            return self._call_openai_compatible_text(prompt)
        if self.provider == "huggingface":
            return self._call_huggingface_text(prompt)
        if self.provider == "gemini":
            return self._call_gemini_text(prompt)
        if self.provider == "anthropic":
            return self._call_anthropic_text(prompt)
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _extract_chat_completion_text(self, response: Any) -> str:
        choices = getattr(response, "choices", None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if isinstance(content, str) and content.strip():
                    return content
                if content is not None:
                    return str(content)
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                message = (choices[0] or {}).get("message") or {}
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                if content is not None:
                    return str(content)
            if isinstance(response.get("output_text"), str):
                return response["output_text"]
        dump = None
        try:
            dump = response.model_dump() if hasattr(response, "model_dump") else None
        except Exception:
            dump = None
        raise ValueError(f"LLM response did not include completion text: {dump or response}")

    def _call_openai_compatible(self, prompt: str, image_base64: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url if self.provider in ("openrouter", "groq") else None,
            timeout=Config.LLM_TIMEOUT_SECONDS,
        )
        media_type = _detect_image_media_type(image_base64)
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a document data extraction engine. Return only valid JSON with no markdown, no explanation, no code fences.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
                    ],
                },
            ],
            "temperature": 0,
            "max_tokens": 4096,
        }
        if self.provider not in ("openrouter", "groq"):
            request_kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**request_kwargs)
        return self._extract_chat_completion_text(response)

    def _call_openai_compatible_text(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url if self.provider in ("openrouter", "groq") else None,
            timeout=Config.LLM_TIMEOUT_SECONDS,
        )
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a document analysis assistant. Return only valid JSON with no markdown, no explanation, no code fences.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 4096,
        }
        if self.provider not in ("openrouter", "groq"):
            request_kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**request_kwargs)
        return self._extract_chat_completion_text(response)

    def _call_huggingface(self, prompt: str, image_base64: str) -> str:
        if not self.api_key:
            raise RuntimeError("HF_TOKEN is required for the huggingface provider")
        InferenceClient = importlib.import_module("huggingface_hub").InferenceClient
        endpoint_target = self.hf_endpoint_url or self.model
        if not self.hf_endpoint_url:
            raise RuntimeError("HF_ENDPOINT_URL is required for huggingface provider")
        client = InferenceClient(model=endpoint_target, token=self.api_key)
        media_type = _detect_image_media_type(image_base64)
        response = client.chat.completions.create(
            model=endpoint_target,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=0,
            max_tokens=4096,
        )
        return self._extract_chat_completion_text(response)

    def _call_huggingface_text(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("HF_TOKEN is required for the huggingface provider")
        InferenceClient = importlib.import_module("huggingface_hub").InferenceClient
        endpoint_target = self.hf_endpoint_url or self.model
        if not self.hf_endpoint_url:
            raise RuntimeError("HF_ENDPOINT_URL is required for huggingface provider")
        client = InferenceClient(model=endpoint_target, token=self.api_key)
        response = client.chat.completions.create(
            model=endpoint_target,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4096,
        )
        return self._extract_chat_completion_text(response)

    def _call_gemini(self, prompt: str, image_base64: str) -> str:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            genai = importlib.import_module("google.generativeai")
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            media_type = _detect_image_media_type(image_base64)
            response = model.generate_content(
                [prompt, {"mime_type": media_type, "data": image_base64}],
                generation_config=genai.GenerationConfig(temperature=0.0, top_p=1.0, max_output_tokens=4096),
            )
            return getattr(response, "text", "{}") or "{}"

    def _call_gemini_text(self, prompt: str) -> str:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            genai = importlib.import_module("google.generativeai")
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                [prompt],
                generation_config=genai.GenerationConfig(temperature=0.0, top_p=1.0, max_output_tokens=4096),
            )
            return getattr(response, "text", "{}") or "{}"

    def _call_anthropic(self, prompt: str, image_base64: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        media_type = _detect_image_media_type(image_base64)
        response = client.messages.create(
            model=self.model,
            # Raised from 2048 → 4096 so long invoices/contracts don't get cut off.
            max_tokens=4096,
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}},
                ],
            }],
        )
        return "".join(
            getattr(item, "text", "") for item in response.content
            if getattr(item, "type", None) == "text"
        ) or "{}"

    def _call_anthropic_text(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return "".join(
            getattr(item, "text", "") for item in response.content
            if getattr(item, "type", None) == "text"
        ) or "{}"

    def _fallback_summary(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        import re

        doc_type = str(context.get("doc_type") or "document").replace("_", " ").strip()
        text = (text or "").strip()

        def _match(patterns: list[str]) -> str | None:
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1).strip() if m.groups() else m.group(0).strip()
            return None

        invoice_number = _match([r"invoice\s*(?:no\.?|number|#|_|:)\s*([A-Z0-9\-/]+)"])
        total_value = _match([r"(?:total|amount\s*due|grand\s*total)\s*[:\-]?\s*₹?\s*([0-9,]+(?:\.[0-9]{1,2})?)"])
        date_value = _match([r"date\s*[:\-]?\s*([A-Za-z0-9,\-/ ]+)"])
        email_value = _match([r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"])

        highlights = []
        sections = []
        if invoice_number:
            highlights.append(f"Invoice number: {invoice_number}")
            sections.append({"title": "Invoice number", "value": invoice_number})
        if total_value:
            highlights.append(f"Total: {total_value}")
            sections.append({"title": "Total", "value": total_value})
        if date_value:
            highlights.append(f"Date: {date_value}")
            sections.append({"title": "Date", "value": date_value})
        if email_value:
            sections.append({"title": "Email", "value": email_value})

        if not sections and text:
            sections.append({"title": "OCR excerpt", "value": " ".join(text.split())[:180]})

        return {
            "summary": f"{doc_type.title()} document detected." + (f" Invoice {invoice_number}." if invoice_number else "") + (f" Total: {total_value}." if total_value else ""),
            "highlights": highlights[:5],
            "document_type": doc_type,
            "sections": sections[:6],
        }


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()