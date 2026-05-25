from __future__ import annotations

import json
from typing import Any

from backend.services.helpers import confidence_from_score


def _bbox_from_ocr(value: str | None, ocr_items: list[dict[str, Any]]) -> dict[str, int] | None:
    if not value:
        return None
    normalized_value = str(value).strip().lower()
    for item in ocr_items:
        text = str(item.get("text", "")).strip().lower()
        if not text:
            continue
        if normalized_value in text or text in normalized_value:
            bbox = item.get("bbox") or {}
            return {"x": int(bbox.get("x", 0)), "y": int(bbox.get("y", 0)), "w": int(bbox.get("w", 0)), "h": int(bbox.get("h", 0))}
    return None


def normalize_extraction_results(extracted: dict[str, Any], ocr_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for field_name, payload in extracted.items():
        if field_name.startswith("_"):
            continue
        value = payload.get("value") if isinstance(payload, dict) else payload
        confidence = payload.get("confidence") if isinstance(payload, dict) else "low"
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
                "confidence": confidence if confidence in {"high", "medium", "low"} else confidence_from_score(0.35),
                "bbox": bbox,
            }
        )
    return results
