from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.models.database import Document, ExtractionResult, TableData, db


documents_bp = Blueprint("documents", __name__)


def _delete_path(path_value: str | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _delete_related_outputs(document: Document) -> None:
    output_folder = Path(current_app.config["OUTPUT_FOLDER"])
    source_stem = Path(document.original_path).stem
    patterns = [
        f"{document.id}.json",
        f"{document.id}.csv",
        f"{document.id}.xlsx",
        f"{source_stem}_page_*.png",
        f"{source_stem}_preprocessed.png",
        f"{source_stem}_preview.png",
    ]
    for pattern in patterns:
        for file_path in output_folder.glob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
            except OSError:
                pass


@documents_bp.get("/api/documents")
def list_documents():
    doc_type = request.args.get("type")
    status = request.args.get("status")
    search = request.args.get("search")

    query = Document.query
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if status:
        query = query.filter(Document.status == status)
    if search:
        query = query.join(ExtractionResult).filter(ExtractionResult.field_value.contains(search))

    documents = []
    seen_hashes: set[str] = set()
    for document in query.order_by(Document.created_at.desc()).all():
        key = document.file_hash or document.id
        if key in seen_hashes:
            continue
        seen_hashes.add(key)
        documents.append(document.to_dict())
    return jsonify({"success": True, "data": documents, "error": None})


@documents_bp.get("/api/documents/<document_id>")
def get_document(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    fields = [item.to_dict() for item in ExtractionResult.query.filter_by(document_id=document.id).all()]
    tables = [item.to_dict() for item in TableData.query.filter_by(document_id=document.id).all()]
    return jsonify({"success": True, "data": {"document": document.to_dict(), "fields": fields, "tables": tables}, "error": None})


@documents_bp.put("/api/documents/<document_id>/fields")
def update_fields(document_id: str):
    payload = request.get_json(silent=True) or {}
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    updated = []
    for item in payload.get("fields", []):
        field_name = item.get("field_name")
        new_value = item.get("field_value")
        if not field_name:
            continue
        result = ExtractionResult.query.filter_by(document_id=document.id, field_name=field_name).first()
        if result is None:
            result = ExtractionResult(document_id=document.id, page_number=1, field_name=field_name, field_value=new_value, confidence=item.get("confidence", "low"), is_corrected=True)
            db.session.add(result)
        else:
            result.field_value = new_value
            result.confidence = item.get("confidence", result.confidence)
            result.is_corrected = True
        updated.append(result.to_dict())

    db.session.commit()
    return jsonify({"success": True, "data": updated, "error": None})


@documents_bp.patch("/api/documents/<document_id>/status")
def update_status(document_id: str):
    payload = request.get_json(silent=True) or {}
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404
    document.status = payload.get("status", document.status)
    db.session.commit()
    return jsonify({"success": True, "data": document.to_dict(), "error": None})


@documents_bp.delete("/api/documents/<document_id>")
def delete_document(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    _delete_path(document.original_path)
    _delete_path(document.preprocessed_path)
    _delete_path(document.preview_path)
    _delete_related_outputs(document)

    db.session.delete(document)
    db.session.commit()
    return jsonify({"success": True, "data": {"deleted": True}, "error": None})


@documents_bp.get("/api/documents/<document_id>/preview")
def preview_document(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None or not document.preview_path:
        return jsonify({"success": False, "data": None, "error": "Preview not available"}), 404
    return send_file(document.preview_path)


@documents_bp.get("/api/documents/<document_id>/original")
def original_document(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404
    return send_file(document.original_path)


@documents_bp.get("/api/documents/<document_id>/preprocessed")
def preprocessed_document(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None or not document.preprocessed_path:
        return jsonify({"success": False, "data": None, "error": "Preprocessed image not available"}), 404
    return send_file(document.preprocessed_path)


@documents_bp.get("/api/documents/<document_id>/tables")
def document_tables(document_id: str):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404
    tables = [item.to_dict() for item in TableData.query.filter_by(document_id=document.id).all()]
    return jsonify({"success": True, "data": tables, "error": None})

