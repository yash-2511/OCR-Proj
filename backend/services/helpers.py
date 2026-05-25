from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def file_to_base64(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return base64.b64encode(data).decode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def safe_json_loads(payload: Any, default: Any = None) -> Any:
    if isinstance(payload, (dict, list)):
        return payload
    if not payload:
        return default
    try:
        return json.loads(payload)
    except Exception:
        return default


def confidence_from_score(score: float | int | None) -> str:
    if score is None:
        return "low"
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def read_json_file(path: str | Path) -> dict:
    return safe_json_loads(Path(path).read_text(encoding="utf-8"), default={})
