from __future__ import annotations

from backend.services.helpers import file_to_base64
from backend.services.llm_client import get_llm_client
from backend.services.bbox_renderer import render_highlighted_bboxes


def classify_document(payload: dict) -> dict:
    image_path = payload.get("image_path") or payload.get("processed_path")
    if not image_path:
        return {"document_type": "form", "confidence": 0.35}

    # If layout context is provided with bbox words, generate a highlighted
    # image that darkens everything except the OCR word bboxes so the LLM
    # can better understand spatial cues.
    layout_context = payload.get("layout_context") or {}
    image_base64 = payload.get("image_base64")
    if not image_base64 and layout_context and isinstance(layout_context.get("bbox_words"), list):
        try:
            bbox_items = [
                {"bbox": w.get("bbox"), "field_name": w.get("text", "word")}
                for w in layout_context.get("bbox_words", [])
            ]
            highlighted_path = render_highlighted_bboxes(image_path, bbox_items)
            image_base64 = file_to_base64(highlighted_path)
        except Exception:
            image_base64 = file_to_base64(image_path)
    else:
        image_base64 = image_base64 or file_to_base64(image_path)
    ocr_text = payload.get("ocr_text") or ""
    document_type_hint = payload.get("document_type")
    layout_context = payload.get("layout_context") or {}
    result = get_llm_client().classify(
        image_base64=image_base64,
        ocr_text=ocr_text,
        document_type_hint=document_type_hint,
        layout_context=layout_context,
    )
    return {"document_type": result.get("doc_type", "form"), "confidence": float(result.get("confidence", 0.35))}
