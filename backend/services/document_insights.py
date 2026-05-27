from __future__ import annotations

from flask import current_app

from backend.models.database import Document
from backend.services.llm_client import get_llm_client


def collect_document_insights(document: Document, fields: list[dict] | None = None, tables: list[dict] | None = None) -> dict:
    structured = document.extraction_result or {}
    extracted_text = str((structured.get("ocr") or {}).get("full_text") or "").strip()
    if not extracted_text:
        extracted_text = "No OCR text could be recovered from this document."

    fields = fields or structured.get("field_annotations") or []
    tables = tables or structured.get("tables") or []
    context = {
        "document_name": document.filename,
        "doc_type": document.doc_type,
        "classification_confidence": document.classification_confidence,
        "page_count": document.page_count,
        "table_count": len(tables),
        "sample_fields": [
            {"field_name": item.get("field_name"), "field_value": item.get("field_value"), "confidence": item.get("confidence")}
            for item in fields[:8]
        ],
        "table_headers": [table.get("headers", []) for table in tables[:3]],
    }

    summary = get_llm_client().summarize(extracted_text[:12000], context=context)

    return {
        "extracted_text": extracted_text,
        "summary": summary.get("summary") or "No summary available.",
        "highlights": summary.get("highlights") or [],
        "document_type": summary.get("document_type") or document.doc_type,
    }