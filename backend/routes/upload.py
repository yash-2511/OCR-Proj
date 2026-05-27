from __future__ import annotations

"""
routes/upload.py — fixes applied
===================================
BUG 1 (synchronous processing blocks the HTTP response): The original
upload_document() called process_document() synchronously, meaning the
HTTP response was held open until OCR + LLM finished — easily 30-120
seconds for a multi-page PDF.  This caused proxy/browser timeouts and
made batch uploads appear to hang.

Fix: upload saves the file and returns a 202 Accepted immediately.
Processing runs in a background daemon thread that has its own app
context.  The frontend polls GET /api/documents/{id} to track status
(status goes "uploaded" → "processing" → "processed" | "failed").

BUG 2 (batch upload doesn't start processing): upload_batch() saved
files and returned IDs but never started extraction.  The frontend had
to fire a separate POST /api/extract/batch call.  Fix: each document is
queued for background processing immediately after saving, same as single
upload.

BUG 3 (no status update before processing starts): Without setting
status="processing" before the thread starts, GET /api/documents/{id}
returned status="uploaded" until the whole pipeline finished, making it
look like nothing was happening.
"""

# from __future__ import annotations

import threading
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from backend.models.database import Batch, Document, db
from backend.services.document_pipeline import process_document
from backend.services.helpers import allowed_file, sha256_bytes


upload_bp = Blueprint("upload", __name__)


def _save_file(file_storage) -> tuple[str, str]:
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    original_name = file_storage.filename or "document"
    suffix = Path(original_name).suffix.lower() or ".bin"
    filename = f"{uuid.uuid4()}{suffix}"
    destination = upload_folder / filename
    file_storage.save(destination)
    return str(destination), original_name


def _hash_uploaded_file(file_storage) -> str:
    stream = file_storage.stream
    position = stream.tell()
    stream.seek(0)
    digest = sha256_bytes(stream.read())
    stream.seek(position)
    return digest


def _existing_document(file_hash: str) -> Document | None:
    return (
        Document.query.filter_by(file_hash=file_hash)
        .order_by(Document.created_at.desc())
        .first()
    )


def _process_in_background(app, document_id: str) -> None:
    """Run process_document() in a daemon thread with its own app context.

    Sets status to 'processing' before starting and 'failed' on error so
    the frontend always sees a meaningful status via polling.
    """
    def _worker():
        with app.app_context():
            doc = db.session.get(Document, document_id)
            if doc is None:
                return
            try:
                doc.status = "processing"
                db.session.commit()
                process_document(document_id)
            except Exception as exc:
                doc = db.session.get(Document, document_id)
                if doc:
                    doc.status = "failed"
                    db.session.commit()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


@upload_bp.post("/api/upload")
def upload_document():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "data": None, "error": "No file uploaded"}), 400

    if not allowed_file(
        uploaded_file.filename or "", current_app.config["ALLOWED_EXTENSIONS"]
    ):
        return jsonify({"success": False, "data": None, "error": "Unsupported file type"}), 400

    file_hash = _hash_uploaded_file(uploaded_file)
    existing = _existing_document(file_hash)
    if existing is not None:
        payload = existing.to_dict()
        payload["duplicate"] = True
        return jsonify({"success": True, "data": payload, "error": None}), 200

    original_path, original_name = _save_file(uploaded_file)
    document = Document(
        filename=original_name,
        original_path=original_path,
        file_hash=file_hash,
        status="uploaded",
    )
    db.session.add(document)
    db.session.commit()

    # Return 202 immediately — processing happens in the background.
    _process_in_background(current_app._get_current_object(), document.id)

    return jsonify({"success": True, "data": document.to_dict(), "error": None}), 202


@upload_bp.post("/api/upload/batch")
def upload_batch():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "data": None, "error": "No files uploaded"}), 400

    batch = Batch(total=0, status="queued", document_ids=[])
    db.session.add(batch)
    db.session.flush()

    document_ids: list[str] = []
    seen_hashes: set[str] = set()
    app = current_app._get_current_object()

    for file_storage in files:
        if not file_storage.filename or not allowed_file(
            file_storage.filename, current_app.config["ALLOWED_EXTENSIONS"]
        ):
            continue

        file_hash = _hash_uploaded_file(file_storage)
        if file_hash in seen_hashes:
            continue

        existing = _existing_document(file_hash)
        if existing is not None:
            seen_hashes.add(file_hash)
            document_ids.append(existing.id)
            continue

        original_path, original_name = _save_file(file_storage)
        document = Document(
            filename=original_name,
            original_path=original_path,
            file_hash=file_hash,
            status="uploaded",
        )
        db.session.add(document)
        db.session.flush()
        document_ids.append(document.id)
        seen_hashes.add(file_hash)

    batch.total = len(document_ids)
    batch.document_ids = list(document_ids)
    db.session.commit()

    # Kick off background processing for every document in the batch.
    for doc_id in document_ids:
        _process_in_background(app, doc_id)

    return (
        jsonify(
            {
                "success": True,
                "data": {"batch_id": batch.id, "document_ids": document_ids},
                "error": None,
            }
        ),
        202,
    )