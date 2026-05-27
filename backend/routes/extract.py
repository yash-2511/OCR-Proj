from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.models.database import Document, db
from backend.services.document_pipeline import process_batch_documents, process_document


extract_bp = Blueprint("extract", __name__)


@extract_bp.post("/api/extract")
def extract_document():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    if not document_id:
        return jsonify({"success": False, "data": None, "error": "document_id is required"}), 400

    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    result = process_document(document.id)
    return jsonify({"success": True, "data": result, "error": None})


@extract_bp.post("/api/extract/batch")
def extract_batch():
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("document_ids") or []
    batch_id = payload.get("batch_id")
    try:
        result = process_batch_documents(document_ids, batch_id=batch_id)
    except ValueError as exc:
        return jsonify({"success": False, "data": None, "error": str(exc)}), 404

    return jsonify({"success": True, "data": result, "error": None})


@extract_bp.post("/api/classify")
def classify():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    document = db.session.get(Document, document_id) if document_id else None
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404
    classification = {"document_type": document.doc_type, "confidence": document.classification_confidence}
    return jsonify({"success": True, "data": classification, "error": None})

