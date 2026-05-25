from __future__ import annotations

from flask import Blueprint, jsonify

from backend.models.database import Batch, db
from backend.services.batch_processor import get_batch


batch_bp = Blueprint("batch", __name__)


@batch_bp.get("/api/batch/<batch_id>/status")
def get_batch_status(batch_id: str):
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        state = get_batch(batch_id)
        if state is None:
            return jsonify({"success": False, "data": None, "error": "Batch not found"}), 404
        return jsonify({"success": True, "data": {"batch_id": batch_id, **state.__dict__}, "error": None})
    return jsonify({"success": True, "data": batch.to_dict(), "error": None})

