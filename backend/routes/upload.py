from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from backend.models.database import Batch, Document, db
from backend.services.batch_processor import start_batch
from backend.services.document_classifier import classify_document
from backend.services.helpers import allowed_file, file_to_base64
from backend.services.helpers import sha256_bytes
from backend.services.pdf_processor import pdf_to_images
from backend.services.image_preprocessor import preprocess_image_file


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
    return Document.query.filter_by(file_hash=file_hash).order_by(Document.created_at.desc()).first()


@upload_bp.post("/api/upload")
def upload_document():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "data": None, "error": "No file uploaded"}), 400

    if not allowed_file(uploaded_file.filename or "", current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"success": False, "data": None, "error": "Unsupported file type"}), 400

    file_hash = _hash_uploaded_file(uploaded_file)
    existing_document = _existing_document(file_hash)
    if existing_document is not None:
        payload = existing_document.to_dict()
        payload["duplicate"] = True
        return jsonify({"success": True, "data": payload, "error": None}), 200

    original_path, original_name = _save_file(uploaded_file)
    document = Document(filename=original_name, original_path=original_path, file_hash=file_hash, status="uploaded")

    if original_path.lower().endswith(".pdf"):
        page_images = pdf_to_images(original_path, current_app.config["OUTPUT_FOLDER"])
        document.page_count = max(1, len(page_images))
        if page_images:
            first_page = page_images[0]["image_path"]
            document.preprocessed_path = preprocess_image_file(first_page)
            image_base64 = file_to_base64(document.preprocessed_path)
            classification = classify_document(image_base64)
            document.doc_type = classification.get("doc_type")
            document.classification_confidence = classification.get("confidence")
    else:
        document.page_count = 1
        document.preprocessed_path = preprocess_image_file(original_path)
        image_base64 = file_to_base64(document.preprocessed_path)
        classification = classify_document(image_base64)
        document.doc_type = classification.get("doc_type")
        document.classification_confidence = classification.get("confidence")

    db.session.add(document)
    db.session.commit()

    return jsonify({"success": True, "data": document.to_dict(), "error": None}), 201


@upload_bp.post("/api/upload/batch")
def upload_batch():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "data": None, "error": "No files uploaded"}), 400

    batch = Batch(total=0, status="queued")
    db.session.add(batch)
    db.session.flush()

    documents: list[str] = []
    seen_hashes: set[str] = set()
    for file_storage in files:
        if not file_storage.filename or not allowed_file(file_storage.filename, current_app.config["ALLOWED_EXTENSIONS"]):
            continue

        file_hash = _hash_uploaded_file(file_storage)
        if file_hash in seen_hashes:
            continue

        existing_document = _existing_document(file_hash)
        if existing_document is not None:
            seen_hashes.add(file_hash)
            documents.append(existing_document.id)
            continue

        original_path, original_name = _save_file(file_storage)
        document = Document(filename=original_name, original_path=original_path, file_hash=file_hash, status="uploaded")
        db.session.add(document)
        db.session.flush()
        documents.append(document.id)
        seen_hashes.add(file_hash)

    batch.total = len(documents)

    db.session.commit()

    def _worker(batch_id: str, document_ids: list[str]) -> None:
        with current_app.app_context():
            batch_record = Batch.query.get(batch_id)
            if batch_record is not None:
                batch_record.status = "running"
                db.session.commit()

    start_batch(batch.id, documents, _worker)
    return jsonify({"success": True, "data": {"batch_id": batch.id, "document_ids": documents}, "error": None}), 201

