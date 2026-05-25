from __future__ import annotations

from pathlib import Path
import uuid
from datetime import datetime

from sqlalchemy import inspect, text
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from backend.services.helpers import sha256_file


db = SQLAlchemy()


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(512), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True, index=True)
    preprocessed_path = db.Column(db.String(512), nullable=True)
    preview_path = db.Column(db.String(512), nullable=True)
    doc_type = db.Column(db.String(64), nullable=True)
    classification_confidence = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="uploaded")
    page_count = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    extraction_results = db.relationship("ExtractionResult", backref="document", lazy=True, cascade="all, delete-orphan")
    tables = db.relationship("TableData", backref="document", lazy=True, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "original_path": self.original_path,
            "file_hash": self.file_hash,
            "preprocessed_path": self.preprocessed_path,
            "preview_path": self.preview_path,
            "doc_type": self.doc_type,
            "classification_confidence": self.classification_confidence,
            "status": self.status,
            "page_count": self.page_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExtractionResult(db.Model):
    __tablename__ = "extraction_results"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=False)
    page_number = db.Column(db.Integer, nullable=False, default=1)
    field_name = db.Column(db.String(128), nullable=False)
    field_value = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.String(16), nullable=False, default="low")
    bbox_x = db.Column(db.Integer, nullable=True)
    bbox_y = db.Column(db.Integer, nullable=True)
    bbox_w = db.Column(db.Integer, nullable=True)
    bbox_h = db.Column(db.Integer, nullable=True)
    is_corrected = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "field_name": self.field_name,
            "field_value": self.field_value,
            "confidence": self.confidence,
            "bbox_x": self.bbox_x,
            "bbox_y": self.bbox_y,
            "bbox_w": self.bbox_w,
            "bbox_h": self.bbox_h,
            "is_corrected": self.is_corrected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TableData(db.Model):
    __tablename__ = "table_data"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=False)
    page_number = db.Column(db.Integer, nullable=False, default=1)
    table_index = db.Column(db.Integer, nullable=False, default=0)
    headers = db.Column(db.JSON, nullable=False, default=list)
    rows = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "table_index": self.table_index,
            "headers": self.headers,
            "rows": self.rows,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    total = db.Column(db.Integer, nullable=False, default=0)
    processed = db.Column(db.Integer, nullable=False, default=0)
    successful = db.Column(db.Integer, nullable=False, default=0)
    failed = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="queued")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "total": self.total,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def ensure_document_hashes() -> None:
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "file_hash" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"))

    documents = Document.query.filter((Document.file_hash.is_(None)) | (Document.file_hash == "")).all()
    if not documents:
        return

    updated = False
    for document in documents:
        path = Path(document.original_path)
        if not path.exists():
            continue
        document.file_hash = sha256_file(path)
        updated = True

    if updated:
        db.session.commit()
