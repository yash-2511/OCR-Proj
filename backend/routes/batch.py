from __future__ import annotations

from flask import Blueprint, jsonify

from backend.models.database import Batch, db
from backend.services.document_pipeline import process_batch_documents
from backend.services.batch_processor import get_batch


batch_bp = Blueprint("batch", __name__)


@batch_bp.get("/api/batch/<batch_id>/status")
def get_batch_status(batch_id: str):
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        state = get_batch(batch_id)
        if state is None:
            return jsonify({"success": False, "data": None, "error": "Batch not found"}), 404
        payload = {"batch_id": batch_id, **state.__dict__}
        payload["document_ids"] = payload.get("documents", [])
        return jsonify({"success": True, "data": payload, "error": None})
    return jsonify({"success": True, "data": batch.to_dict(), "error": None})


@batch_bp.get("/api/batch")
def list_batches():
    batches = []
    for batch in Batch.query.order_by(Batch.created_at.desc()).all():
        payload = batch.to_dict()
        payload["name"] = f"Batch {batch.created_at.strftime('%Y-%m-%d %H:%M')}"
        batches.append(payload)
    return jsonify({"success": True, "data": batches, "error": None})


@batch_bp.post("/api/batch/<batch_id>/process")
def process_batch(batch_id: str):
    batch = db.session.get(Batch, batch_id)
    document_ids = list(batch.document_ids or []) if batch is not None else []

    if not document_ids:
        state = get_batch(batch_id)
        document_ids = list(getattr(state, "documents", []) or []) if state is not None else []

    if not document_ids:
        return jsonify({"success": False, "data": None, "error": "Batch has no documents to process"}), 400

    try:
        result = process_batch_documents(document_ids, batch_id=batch_id)
    except ValueError as exc:
        return jsonify({"success": False, "data": None, "error": str(exc)}), 404

    return jsonify({"success": True, "data": {"batch_id": batch_id, **result}, "error": None})

