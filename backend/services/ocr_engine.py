from __future__ import annotations

"""
ocr_engine.py — fixes applied
================================
BUG 1 (reader re-initialised on every call): load_ocr_reader() was
called inside extract_ocr() when reader=None.  EasyOCR initialisation
takes 3-10 seconds (model loading).  For a 10-page PDF this added 30-100
seconds to total processing time.  Fix: the pipeline caches the reader on
app.config["OCR_READER"]; extract_ocr() now simply accepts it.  A
module-level _READER cache is also provided as a second layer for calls
made outside a Flask context (tests, scripts).

BUG 2 (image loaded via cv2.imread then passed raw to EasyOCR): EasyOCR
accepts a file path string directly and handles its own loading correctly
for all JPEG/PNG/WEBP variants.  Passing a cv2 numpy array is fine but
loses the benefit of EasyOCR's internal PIL-based loading which handles
EXIF rotation automatically.  Fix: pass the path string to readtext().

BUG 3 (no minimum confidence filter): OCR words with near-zero confidence
(garbled characters, noise) were included in full_text, polluting the
string fed to the LLM.  Fix: filter out words with confidence < 0.3.
"""

from pathlib import Path
from typing import Any
import warnings

from backend.services.helpers import normalize_bbox

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

# Module-level singleton — used when called outside a Flask app context.
_READER = None


def load_ocr_reader(languages: list[str] | None = None, gpu: bool = False):
    global _READER
    if _READER is not None:
        return _READER
    try:
        import easyocr

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*pin_memory.*no accelerator is found.*",
                category=UserWarning,
            )
            _READER = easyocr.Reader(languages or ["en"], gpu=gpu)
            return _READER
    except Exception:
        return None


def _normalize_input(payload: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {"processed_path": str(payload)}


# Minimum confidence below which an OCR word is considered noise.
_MIN_CONFIDENCE = 0.30


def extract_ocr(payload: dict[str, Any] | str, reader: Any | None = None) -> dict[str, Any]:
    payload = _normalize_input(payload)
    image_path = payload.get("processed_path") or payload.get("image_path")
    if not image_path:
        return {"full_text": "", "words": []}

    if reader is None:
        reader = load_ocr_reader()
    if reader is None:
        return {"full_text": "", "words": []}

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*pin_memory.*no accelerator is found.*",
                category=UserWarning,
            )
            # Pass the path string directly so EasyOCR handles EXIF rotation.
            results = reader.readtext(str(image_path), detail=1, paragraph=False)

        words: list[dict[str, Any]] = []
        text_parts: list[str] = []

        for bbox_poly, text, confidence in results:
            # Filter low-confidence noise before it contaminates the LLM prompt.
            if float(confidence) < _MIN_CONFIDENCE:
                continue

            cleaned_text = str(text).strip()
            if not cleaned_text:
                continue

            text_parts.append(cleaned_text)

            # Normalise polygon → [x1, y1, x2, y2]
            norm = normalize_bbox(bbox_poly)
            if norm is None:
                xs = [point[0] for point in bbox_poly]
                ys = [point[1] for point in bbox_poly]
                norm = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]

            words.append({
                "text": cleaned_text,
                "confidence": float(confidence),
                "bbox": norm,
            })

        return {"full_text": " ".join(text_parts).strip(), "words": words}
    except Exception:
        return {"full_text": "", "words": []}