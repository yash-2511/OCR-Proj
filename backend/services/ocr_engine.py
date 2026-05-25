from __future__ import annotations

from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


def load_ocr_reader(languages: list[str] | None = None, gpu: bool = False):
    try:
        import easyocr

        return easyocr.Reader(languages or ["en"], gpu=gpu)
    except Exception:
        return None


def extract_ocr(image_path: str, reader: Any) -> list[dict[str, Any]]:
    if reader is None:
        return []
    try:
        if cv2 is None:
            return []
        image = cv2.imread(image_path)
        if image is None:
            return []
        results = reader.readtext(image, detail=1, paragraph=False)
        words: list[dict[str, Any]] = []
        for bbox, text, confidence in results:
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))
            words.append({"text": text, "confidence": float(confidence), "bbox": {"x": x, "y": y, "w": w, "h": h}})
        return words
    except Exception:
        return []
