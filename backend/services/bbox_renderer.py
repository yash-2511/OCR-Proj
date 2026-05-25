from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageDraw = None
    ImageFont = None


def _field_color(field_name: str) -> tuple[int, int, int]:
    lowered = field_name.lower()
    if any(token in lowered for token in ["amount", "total", "subtotal", "tax", "price"]):
        return (46, 204, 113)
    if "date" in lowered:
        return (52, 152, 219)
    if any(token in lowered for token in ["name", "vendor", "customer"]):
        return (243, 156, 18)
    return (149, 165, 166)


def render_bounding_boxes(image_path: str, extraction_results: list[dict[str, Any]], output_path: str | None = None) -> str:
    if Image is None or ImageDraw is None:
        return image_path

    source = Path(image_path)
    target = Path(output_path) if output_path else source.with_name(f"{source.stem}_preview.png")
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)

    for item in extraction_results:
        bbox = item.get("bbox") or {}
        x = bbox.get("x")
        y = bbox.get("y")
        w = bbox.get("w")
        h = bbox.get("h")
        if None in {x, y, w, h}:
            continue
        color = _field_color(item.get("field_name", "other"))
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        draw.rectangle([x, max(0, y - 18), x + max(80, len(item.get("field_name", "")) * 8), y], fill=color)
        draw.text((x + 4, max(0, y - 16)), item.get("field_name", "field"), fill=(255, 255, 255))

    image.save(target)
    return str(target)
