from __future__ import annotations

from backend.services.llm_client import get_llm_client


def classify_document(image_base64: str) -> dict:
    return get_llm_client().classify(image_base64)
