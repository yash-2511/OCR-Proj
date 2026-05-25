from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.models.database import Batch, Document, ExtractionResult, TableData, db
from backend.services.bbox_renderer import render_bounding_boxes
from backend.services.export_service import build_document_payload
from backend.services.field_extractor import normalize_extraction_results
from backend.services.helpers import file_to_base64
from backend.services.ocr_engine import extract_ocr
from backend.services.pdf_processor import pdf_to_images
from backend.services.table_extractor import extract_tables
from backend.services.vision_extractor import extract_with_schema
from backend.services.image_preprocessor import preprocess_image_file
from backend.services.batch_processor import update_batch
from backend.services.ocr_engine import load_ocr_reader


extract_bp = Blueprint("extract", __name__)


def _extract_document(document: Document) -> dict:
    if document.original_path.lower().endswith(".pdf"):
        page_images = pdf_to_images(document.original_path, current_app.config["OUTPUT_FOLDER"])
    else:
        page_images = [{"page_number": 1, "image_path": document.preprocessed_path or preprocess_image_file(document.original_path)}]

    all_fields: list[dict] = []
    all_tables: list[dict] = []
    reader = current_app.config.get("OCR_READER")
    if reader is None:
        reader = load_ocr_reader()
        current_app.config["OCR_READER"] = reader

    for page in page_images:
        image_path = page["image_path"]
        image_base64 = file_to_base64(image_path)
        ocr_items = extract_ocr(image_path, reader)
        doc_type = document.doc_type or "form"
        extracted = extract_with_schema(image_base64, doc_type)
        normalized = normalize_extraction_results(extracted, ocr_items)

        for item in normalized:
            result = ExtractionResult(
                document_id=document.id,
                page_number=page.get("page_number", 1),
                field_name=item["field_name"],
                field_value=item.get("field_value"),
                confidence=item.get("confidence", "low"),
                bbox_x=(item.get("bbox") or {}).get("x"),
                bbox_y=(item.get("bbox") or {}).get("y"),
                bbox_w=(item.get("bbox") or {}).get("w"),
                bbox_h=(item.get("bbox") or {}).get("h"),
            )
            db.session.add(result)
            all_fields.append(item)

        tables = extract_tables(image_path, ocr_items)
        for table_index, table in enumerate(tables):
            table_record = TableData(document_id=document.id, page_number=page.get("page_number", 1), table_index=table_index, headers=table.get("headers", []), rows=table.get("rows", []))
            db.session.add(table_record)
            all_tables.append(table)

        if not document.preview_path:
            document.preview_path = render_bounding_boxes(image_path, normalized)

    document.status = "extracted"
    db.session.commit()
    return build_document_payload(document, all_fields, all_tables)


@extract_bp.post("/api/extract")
def extract_document():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    if not document_id:
        return jsonify({"success": False, "data": None, "error": "document_id is required"}), 400

    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    result = _extract_document(document)
    return jsonify({"success": True, "data": result, "error": None})


@extract_bp.post("/api/extract/batch")
def extract_batch():
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("document_ids") or []
    batch_id = payload.get("batch_id")
    documents = Document.query.filter(Document.id.in_(document_ids)).all()
    if not documents:
        return jsonify({"success": False, "data": None, "error": "No documents found"}), 404

    processed = 0
    successful = 0
    failed = 0
    results = []
    for document in documents:
        processed += 1
        try:
            results.append(_extract_document(document))
            successful += 1
        except Exception:
            failed += 1

    if batch_id:
        update_batch(batch_id, total=len(documents), processed=processed, successful=successful, failed=failed)
        batch_record = db.session.get(Batch, batch_id)
        if batch_record is not None:
            batch_record.total = len(documents)
            batch_record.processed = processed
            batch_record.successful = successful
            batch_record.failed = failed
            batch_record.status = "done" if failed == 0 else "failed"
            db.session.commit()

    return jsonify({"success": True, "data": {"results": results, "processed": processed, "successful": successful, "failed": failed}, "error": None})


@extract_bp.post("/api/classify")
def classify():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    document = db.session.get(Document, document_id) if document_id else None
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404
    classification = {"doc_type": document.doc_type, "confidence": document.classification_confidence}
    return jsonify({"success": True, "data": classification, "error": None})

