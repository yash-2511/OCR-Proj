from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'documents.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Upload limits ──────────────────────────────────────────────────────────
    # Raised from 20 MB → 200 MB so multi-page PDFs and batch uploads don't get
    # rejected by Flask before any code runs (was the primary cause of 413 errors).
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "200"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    UPLOAD_FOLDER = str(BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads"))
    OUTPUT_FOLDER = str(BASE_DIR / os.getenv("OUTPUT_FOLDER", "outputs"))
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    # Raised from 60 s → 120 s so large documents don't time out mid-extraction.
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    HF_ENDPOINT_URL = os.getenv("HF_ENDPOINT_URL", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # ── PDF processing ────────────────────────────────────────────────────────
    # Render at 1.5× (150 DPI equivalent) instead of 2×. This halves memory use
    # for large PDFs while still giving EasyOCR enough resolution to read text.
    PDF_RENDER_SCALE = float(os.getenv("PDF_RENDER_SCALE", "1.5"))
    # Hard cap: only process the first N pages of a very long PDF to prevent OOM.
    PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "20"))

    # ── Background processing ─────────────────────────────────────────────────
    # Number of worker threads for async document processing.
    PROCESSING_THREADS = int(os.getenv("PROCESSING_THREADS", "2"))