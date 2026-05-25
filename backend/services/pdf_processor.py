from __future__ import annotations

from pathlib import Path

try:
    import fitz
except Exception:  # pragma: no cover - optional dependency
    fitz = None


def pdf_to_images(pdf_path: str, output_folder: str) -> list[dict]:
    if fitz is None:
        return []

    source = Path(pdf_path)
    destination = Path(output_folder)
    destination.mkdir(parents=True, exist_ok=True)
    document = fitz.open(source)
    page_images: list[dict] = []
    try:
        for page_index in range(len(document)):
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = destination / f"{source.stem}_page_{page_index + 1}.png"
            pixmap.save(str(image_path))
            page_images.append({"page_number": page_index + 1, "image_path": str(image_path), "width": pixmap.width, "height": pixmap.height})
    finally:
        document.close()
    return page_images
