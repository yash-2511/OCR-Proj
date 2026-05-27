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


def normalize_bbox(bbox: Any) -> list[int] | None:
    """
    Normalize bbox to [x1, y1, x2, y2]. Accepts:
    - [x, y, w, h]
    - [x1, y1, x2, y2]
    - dict with keys {x,y,w,h}
    - EasyOCR polygon [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
    Returns None for invalid input.
    """
    if not bbox:
        return None
    # EasyOCR polygon
    try:
        # polygon like [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        if isinstance(bbox, list) and len(bbox) > 0 and isinstance(bbox[0], (list, tuple)):
            xs = [int(p[0]) for p in bbox]
            ys = [int(p[1]) for p in bbox]
            return [min(xs), min(ys), max(xs), max(ys)]
        if isinstance(bbox, dict):
            x = int(bbox.get("x", 0))
            y = int(bbox.get("y", 0))
            w = int(bbox.get("w", 0))
            h = int(bbox.get("h", 0))
            return [x, y, x + w, y + h]
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            a, b, c, d = bbox
            # Heuristic: if c and d look like width/height (small), convert
            try:
                a_f = float(a)
                b_f = float(b)
                c_f = float(c)
                d_f = float(d)
            except Exception:
                return None
            # If c is width (<= image width heuristics unknown), assume it's w/h when c < a
            if c_f <= 0 or d_f <= 0:
                return None
            # If c looks like x2 (greater than a), and d greater than b, assume [x1,y1,x2,y2]
            if c_f > a_f and d_f > b_f:
                return [int(a_f), int(b_f), int(c_f), int(d_f)]
            # Otherwise treat as [x,y,w,h]
            return [int(a_f), int(b_f), int(a_f + c_f), int(b_f + d_f)]
    except Exception:
        return None
    return None
