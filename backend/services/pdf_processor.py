from __future__ import annotations

"""
pdf_processor.py — fixes applied
==================================
BUG 1 (memory / OOM on large PDFs): The original used a fixed
fitz.Matrix(2, 2) which renders every page at 2× (≈ 192 DPI).  For a
20-page PDF with A4 pages this creates ~20 × 4.5 MB = 90 MB of raw
pixel data before any OCR starts, often causing OOM on servers with
limited RAM.

Fix: read the scale factor from Config.PDF_RENDER_SCALE (default 1.5 =
144 DPI — plenty for EasyOCR) and honour Config.PDF_MAX_PAGES to hard-cap
how many pages are processed per document.

BUG 2 (no page limit): A 100-page contract would be processed entirely,
blocking the request thread for many minutes.  The page cap makes the
system fail gracefully and fast while still extracting the most important
content.
"""

from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None


def _render_scale() -> float:
    """Read the render scale from Flask config when inside an app context,
    fall back to 1.5 otherwise (e.g. during tests)."""
    try:
        from flask import current_app
        return float(current_app.config.get("PDF_RENDER_SCALE", 1.5))
    except RuntimeError:
        return 1.5


def _max_pages() -> int:
    try:
        from flask import current_app
        return int(current_app.config.get("PDF_MAX_PAGES", 20))
    except RuntimeError:
        return 20


def pdf_to_images(pdf_path: str, output_folder: str) -> list[dict]:
    if fitz is None:
        return []

    source = Path(pdf_path)
    destination = Path(output_folder)
    destination.mkdir(parents=True, exist_ok=True)

    scale = _render_scale()
    max_pages = _max_pages()

    doc = fitz.open(source)
    page_images: list[dict] = []
    try:
        total = len(doc)
        pages_to_render = min(total, max_pages)
        matrix = fitz.Matrix(scale, scale)

        for page_index in range(pages_to_render):
            page = doc[page_index]
            # alpha=False avoids an unnecessary 4th channel that triples memory.
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = destination / f"{source.stem}_page_{page_index + 1}.png"
            pixmap.save(str(image_path))
            # Explicitly delete the pixmap to free memory before the next page.
            del pixmap
            page_images.append(
                {
                    "page_number": page_index + 1,
                    "image_path": str(image_path),
                    "total_pages": total,
                    "pages_rendered": pages_to_render,
                }
            )
    finally:
        doc.close()

    return page_images


def convert_pdf_to_images(pdf_path: str, output_folder: str) -> list[str]:
    return [page["image_path"] for page in pdf_to_images(pdf_path, output_folder)]