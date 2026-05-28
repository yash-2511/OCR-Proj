from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import event

from backend.config import Config
from backend.models.database import db, ensure_batch_document_ids, ensure_document_extraction_results, ensure_document_hashes
from backend.routes import auth_bp, batch_bp, documents_bp, export_bp, extract_bp, upload_bp


def _ensure_directory(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    _ensure_directory(app.config["UPLOAD_FOLDER"])
    _ensure_directory(app.config["OUTPUT_FOLDER"])

    CORS(app)
    db.init_app(app)

    app.register_blueprint(upload_bp)
    app.register_blueprint(extract_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(auth_bp)

    @app.get("/")
    def main():
        return """
    <h2>Flask Server running successfully at PORT 5000</h2>
    <h2><a href="http://localhost:3000" target="_blank">
        Visit Frontend
    </a></h2>
    """

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "data": {"status": "ok"}, "error": None})

    @app.get("/api/stats")
    def stats():
        from backend.models.database import Batch, Document

        return jsonify(
            {
                "success": True,
                "data": {
                    "documents": Document.query.count(),
                    "batches": Batch.query.count(),
                },
                "error": None,
            }
        )

    with app.app_context():
        # Only apply SQLite-specific PRAGMAs when running SQLite locally.
        # Running these against PostgreSQL corrupts the connection's transaction
        # state before db.create_all() executes, causing the
        # "InFailedSqlTransaction" cascade seen on Render/Supabase.
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            @event.listens_for(db.engine, "connect")
            def _configure_sqlite(connection, _record):  # pragma: no cover
                cursor = connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=30000")
                cursor.close()

        db.create_all()
        ensure_document_extraction_results()
        ensure_document_hashes()
        ensure_batch_document_ids()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_ENV", "development") == "development",
    )