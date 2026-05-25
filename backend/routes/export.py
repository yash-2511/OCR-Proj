from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.models.database import Batch, Document, ExtractionResult, TableData, db
from backend.services.export_service import build_document_payload, export_batch_zip, export_csv_file, export_excel_file, export_json_file


export_bp = Blueprint("export", __name__)


@export_bp.post("/api/export")
def export_document():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    export_format = (payload.get("format") or "json").lower()
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"success": False, "data": None, "error": "Document not found"}), 404

    fields = [item.to_dict() for item in ExtractionResult.query.filter_by(document_id=document.id).all()]
    tables = [item.to_dict() for item in TableData.query.filter_by(document_id=document.id).all()]
    payload_data = build_document_payload(document, fields, tables)
    output_dir = Path(current_app.config["OUTPUT_FOLDER"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if export_format == "csv":
        output_path = output_dir / f"{document.id}.csv"
        export_csv_file(fields, str(output_path))
    elif export_format == "excel":
        output_path = output_dir / f"{document.id}.xlsx"
        export_excel_file(payload_data, str(output_path))
    else:
        output_path = output_dir / f"{document.id}.json"
        export_json_file(payload_data, str(output_path))

    return send_file(str(output_path), as_attachment=True)


@export_bp.post("/api/export/batch/<batch_id>")
def export_batch(batch_id: str):
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        return jsonify({"success": False, "data": None, "error": "Batch not found"}), 404

    documents = Document.query.filter(Document.status != "failed").all()
    output_dir = Path(current_app.config["OUTPUT_FOLDER"])
    output_dir.mkdir(parents=True, exist_ok=True)

    exported_files = []
    for document in documents:
        fields = [item.to_dict() for item in ExtractionResult.query.filter_by(document_id=document.id).all()]
        tables = [item.to_dict() for item in TableData.query.filter_by(document_id=document.id).all()]
        payload = build_document_payload(document, fields, tables)
        file_path = output_dir / f"{document.id}.json"
        export_json_file(payload, str(file_path))
        exported_files.append(str(file_path))

    zip_path = output_dir / f"batch_{batch_id}.zip"
    export_batch_zip(exported_files, str(zip_path))
    return send_file(str(zip_path), as_attachment=True)

