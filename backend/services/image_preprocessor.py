from __future__ import annotations

"""
image_preprocessor.py — fixes applied
======================================
BUG 1 (deskew): The original _deskew() called cv2.minAreaRect() on
*bright* pixel coordinates of the raw BGR image.  On a normal document
(white background, dark text) almost every pixel is bright, so the
bounding rectangle covers the whole image and the returned angle is near 0
even when the page is badly tilted.  Fix: convert to grayscale, invert so
TEXT pixels are bright (not the background), find those contours, then
compute the skew angle.

BUG 2 (border strip): The original _strip_borders() used
THRESH_BINARY_INV on grayscale which inverts the whole image.  On a clean
white-background scan the "non-zero" region is the entire image and
cv2.findNonZero returns None or the full rectangle, so no border is
removed.  Fix: work on the inverted image so actual ink pixels are
non-zero, then crop to the tight bounding box of those pixels — but only
if the crop removes at least a meaningful margin (>10 px on any side).

BUG 3 (noise detection): The Laplacian variance threshold of 500 is
arbitrary and often mis-classifies phone photos as "clean digital"
documents, skipping denoising.  Raised to 300 and combined with a mean
brightness check to be more conservative.
"""

from pathlib import Path

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover
    cv2 = None
    np = None


def _deskew(image):
    """Detect and correct page rotation/skew.

    Works by finding the orientation of the actual ink pixels (dark on
    white) rather than the bright background pixels.
    """
    if cv2 is None or np is None:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Invert: text pixels become white (255), background becomes black (0).
    inverted = cv2.bitwise_not(gray)

    # Threshold to get a binary mask of ink pixels.
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Collect coordinates of ink pixels.
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < 50:
        # Too few ink pixels — nothing to skew-correct.
        return image

    # Fit a rotated bounding box to the ink pixel cloud.
    angle = cv2.minAreaRect(coords)[-1]

    # cv2.minAreaRect returns angles in [-90, 0).
    # Normalize: angles close to -90 mean the rect is nearly vertical → small
    # positive correction needed; angles close to 0 are fine.
    if angle < -45:
        angle = 90 + angle  # e.g. -89° → +1° (correct a slight CW tilt)
    else:
        angle = angle        # e.g. -3° → rotate CCW by 3°

    # Ignore very small skew (< 0.5°) to avoid resampling artefacts on clean docs.
    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _strip_borders(image):
    """Remove solid black/dark borders left by scanner platens.

    Only crops if there is a meaningful border to remove (> 10 px on at
    least one side) so clean images are returned untouched.
    """
    if cv2 is None or np is None:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Find ink pixels (dark on white document).
    inverted = cv2.bitwise_not(gray)
    _, binary = cv2.threshold(inverted, 30, 255, cv2.THRESH_BINARY)

    coords = cv2.findNonZero(binary)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    ih, iw = image.shape[:2]

    # Only strip if we'd actually remove a meaningful border.
    margin = 10
    if x < margin and y < margin and (x + w) > (iw - margin) and (y + h) > (ih - margin):
        return image  # No real border to remove.

    return image[y: y + h, x: x + w]


def preprocess_image(payload: dict[str, str | None]) -> dict:
    image_path = payload.get("image_path")
    if not image_path:
        return {"original_path": None, "processed_path": None, "operations": []}

    if cv2 is None or np is None:
        return {"original_path": image_path, "processed_path": image_path, "operations": []}

    source_path = Path(image_path)
    target_path = Path(
        payload.get("output_path")
        or source_path.with_name(f"{source_path.stem}_preprocessed.png")
    )

    try:
        image = cv2.imread(str(source_path))
        if image is None:
            return {"original_path": image_path, "processed_path": image_path, "operations": []}

        operations: list[str] = []

        # 1. Deskew (fixed — now operates on ink pixels not background).
        image = _deskew(image)
        operations.append("deskew")

        # 2. Border removal (fixed — only strips if a real border exists).
        image = _strip_borders(image)
        operations.append("border_removal")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 3. Decide if the image is a clean digital render or a noisy scan/photo.
        #    Use both Laplacian variance AND mean brightness.
        #    Clean digital: high variance (sharp edges), high mean brightness (white bg).
        noise_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        mean_brightness = float(np.mean(gray))
        # Raised threshold from 500 → 300 and require bright background.
        is_clean_digital = noise_variance > 300 and mean_brightness > 180

        if is_clean_digital:
            # Soft CLAHE only — don't binarise clean renders (destroys colour text).
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            operations.append("clahe_soft")
            out_img = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            cv2.imwrite(str(target_path), out_img)
        else:
            # Noisy photo / bad scan: denoise → CLAHE → adaptive binarise.
            denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
            operations.append("bilateral_denoise")

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            operations.append("clahe")

            # blockSize=21 works better on lower-DPI phone photos than 15.
            binarized = cv2.adaptiveThreshold(
                enhanced, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                21, 10,
            )
            operations.append("adaptive_binarize")

            cv2.imwrite(str(target_path), binarized)

        return {
            "original_path": str(source_path),
            "processed_path": str(target_path),
            "operations": operations,
        }
    except Exception:
        return {"original_path": str(source_path), "processed_path": str(source_path), "operations": []}


def preprocess_image_file(image_path: str, output_path: str | None = None) -> str:
    result = preprocess_image({"image_path": image_path, "output_path": output_path})
    return result.get("processed_path") or image_path