from __future__ import annotations

from pathlib import Path

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - fallback when optional deps are unavailable
    cv2 = None
    np = None


def _deskew(image):
    if cv2 is None or np is None:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    coords = np.column_stack(np.where(gray > 0))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_image_file(image_path: str, output_path: str | None = None) -> str:
    if cv2 is None or np is None:
        return image_path

    source_path = Path(image_path)
    target_path = Path(output_path) if output_path else source_path.with_name(f"{source_path.stem}_preprocessed.png")
    try:
        image = cv2.imread(str(source_path))
        if image is None:
            return image_path

        image = _deskew(image)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
        _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(str(target_path), threshold)
        return str(target_path)
    except Exception:
        return image_path
