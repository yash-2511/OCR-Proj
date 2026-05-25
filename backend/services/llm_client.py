from __future__ import annotations

import json
import os
import re
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


def _extract_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        return safe_json_loads(match.group(0), default={}) or {}


@dataclass
class LLMClient:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.provider = (self.provider or Config.LLM_PROVIDER).lower()
        self.model = self.model or Config.LLM_MODEL
        self.api_key = self.api_key or Config.LLM_API_KEY
        self.base_url = self.base_url or Config.OPENROUTER_BASE_URL

    def classify(self, image_base64: str) -> dict[str, Any]:
        prompt = (
            "Classify this document into exactly one of these categories: "
            + ", ".join(DOC_TYPES)
            + "\nReturn only JSON: {\"doc_type\":\"<type>\", \"confidence\":0.0}"
        )
        try:
            payload = self._call(prompt=prompt, image_base64=image_base64)
            data = _extract_json(payload)
            doc_type = data.get("doc_type") if data.get("doc_type") in DOC_TYPES else "form"
            confidence = float(data.get("confidence", 0.35) or 0.35)
            return {"doc_type": doc_type, "confidence": max(0.0, min(1.0, confidence))}
        except Exception:
            return {"doc_type": "form", "confidence": 0.35}

    def extract(self, image_base64: str, schema: dict, doc_type: str) -> dict[str, Any]:
        fields = schema.get("fields", []) if isinstance(schema, dict) else []
        prompt_lines = []
        for field in fields:
            line = f"- {field.get('name')} ({field.get('type')})"
            if field.get("required"):
                line += " required"
            if field.get("type") == "table" and field.get("columns"):
                line += f" columns: {', '.join(field.get('columns', []))}"
            prompt_lines.append(line)

        prompt = (
            f"Document type: {doc_type}\n\n"
            f"Extract the following fields:\n" + "\n".join(prompt_lines) + "\n\n"
            "Rules:\n"
            "- Return null for any field not found in the document\n"
            "- Currency values: numbers only, no symbols\n"
            "- Dates: ISO format YYYY-MM-DD\n"
            "- Tables/line_items: return as array of objects\n"
            "- Add a '_confidence' key for each field: 'high', 'medium', or 'low'\n"
            "- Return ONLY a JSON object, nothing else"
        )
        try:
            payload = self._call(prompt=prompt, image_base64=image_base64)
            data = _extract_json(payload)
            if not isinstance(data, dict):
                return self._fallback_extract(fields)
            return self._normalize_extract(data, fields)
        except Exception:
            return self._fallback_extract(fields)

    def _normalize_extract(self, data: dict, fields: list[dict]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in fields:
            name = field.get("name")
            if not name:
                continue
            raw_value = data.get(name)
            if isinstance(raw_value, dict) and {"value", "confidence"}.issubset(raw_value.keys()):
                value = raw_value.get("value")
                confidence = raw_value.get("confidence") or data.get(f"{name}_confidence") or data.get("_confidence") or "low"
            else:
                value = raw_value
                confidence = data.get(f"{name}_confidence") or data.get("_confidence") or "low"
            normalized[name] = {"value": value, "confidence": confidence}
        for key, value in data.items():
            if key.endswith("_confidence") or key in normalized:
                continue
            if isinstance(value, dict) and {"value", "confidence"}.issubset(value.keys()):
                normalized[key] = value
            else:
                normalized[key] = {"value": value, "confidence": confidence_from_score(value.get("score")) if isinstance(value, dict) else "low"}
        return normalized

    def _fallback_extract(self, fields: list[dict]) -> dict[str, Any]:
        return {field.get("name"): {"value": None, "confidence": "low"} for field in fields if field.get("name")}

    def _call(self, prompt: str, image_base64: str) -> str:
        if self.provider == "openai" or self.provider == "openrouter":
            return self._call_openai_compatible(prompt, image_base64)
        if self.provider == "gemini":
            return self._call_gemini(prompt, image_base64)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, image_base64)
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _call_openai_compatible(self, prompt: str, image_base64: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url if self.provider == "openrouter" else None)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a document data extraction engine. Return only valid JSON with no markdown, no explanation, no code fences."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}]},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    def _call_gemini(self, prompt: str, image_base64: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": image_base64},
        ])
        return getattr(response, "text", "{}") or "{}"

    def _call_anthropic(self, prompt: str, image_base64: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                    ],
                }
            ],
        )
        parts = []
        for item in response.content:
            if getattr(item, "type", None) == "text":
                parts.append(getattr(item, "text", ""))
        return "".join(parts) or "{}"


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()
