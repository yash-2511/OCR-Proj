from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageDraw = None
    ImageFont = None

from backend.services.helpers import normalize_bbox


def _field_color(field_name: str) -> tuple[int, int, int]:
    lowered = field_name.lower()
    if any(token in lowered for token in ["amount", "total", "subtotal", "tax", "price"]):
        return (46, 204, 113)
    if "date" in lowered:
        return (52, 152, 219)
    if any(token in lowered for token in ["name", "vendor", "customer"]):
        return (243, 156, 18)
    return (149, 165, 166)


def _normalize_bbox(bbox: Any) -> tuple[int, int, int, int] | None:
    norm = normalize_bbox(bbox)
    if norm is None:
        return None
    x1, y1, x2, y2 = norm
    return int(x1), int(y1), int(x2), int(y2)


def render_bounding_boxes(image_path: str, extraction_results: list[dict[str, Any]], output_path: str | None = None) -> str:
    if Image is None or ImageDraw is None:
        return image_path

    source = Path(image_path)
    target = Path(output_path) if output_path else source.with_name(f"{source.stem}_preview.png")
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)

    for item in extraction_results:
        bbox = _normalize_bbox(item.get("bbox"))
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        color = _field_color(item.get("field_name", "other"))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        draw.rectangle([x1, max(0, y1 - 18), x1 + max(80, len(item.get("field_name", "")) * 8), y1], fill=color)
        draw.text((x1 + 4, max(0, y1 - 16)), item.get("field_name", "field"), fill=(255, 255, 255))

    image.save(target)
    return str(target)


def render_highlighted_bboxes(image_path: str, bbox_items: list[dict[str, Any]] | None, output_path: str | None = None) -> str:
    """Create an image that darkens everything except the provided bboxes.

    `bbox_items` is a list of dicts each containing a `bbox` key in either
    [x, y, w, h] or {x,y,w,h} form. Returns the path to the generated image.
    """
    if Image is None or ImageDraw is None:
        return image_path

    if not bbox_items:
        return image_path

    source = Path(image_path)
    target = Path(output_path) if output_path else source.with_name(f"{source.stem}_highlight.png")
    image = Image.open(source).convert("RGBA")

    # Build mask: opaque (255) by default, transparent (0) in bbox regions
    mask = Image.new("L", image.size, color=255)
    draw_mask = ImageDraw.Draw(mask)

    normalized_bboxes: list[tuple[int, int, int, int]] = []
    for item in bbox_items:
        bbox = _normalize_bbox(item.get("bbox"))
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        normalized_bboxes.append((x1, y1, x2, y2))
        draw_mask.rectangle([x1, y1, x2, y2], fill=0)

    # Create dark overlay with alpha controlled by mask
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 180))
    overlay.putalpha(mask)

    composed = Image.alpha_composite(image, overlay)

    # Draw colored outlines for each bbox on top
    draw = ImageDraw.Draw(composed)
    for item, (x1, y1, x2, y2) in zip(bbox_items, normalized_bboxes):
        color = _field_color(item.get("field_name", "other"))
        draw.rectangle([x1, y1, x2, y2], outline=color + (255,), width=3)

    composed.convert("RGB").save(target)
    return str(target)
