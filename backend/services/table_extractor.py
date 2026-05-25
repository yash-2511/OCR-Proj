from __future__ import annotations

from collections import defaultdict
from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


def extract_tables(image_path: str, ocr_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ocr_items:
        return []

    rows_by_y: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in ocr_items:
        bbox = item.get("bbox") or {}
        y = int(bbox.get("y", 0) // 25)
        rows_by_y[y].append(item)

    ordered_rows = [sorted(items, key=lambda entry: entry.get("bbox", {}).get("x", 0)) for _, items in sorted(rows_by_y.items(), key=lambda pair: pair[0])]
    if len(ordered_rows) < 2:
        return []

    headers = [entry.get("text", "") for entry in ordered_rows[0]]
    table_rows = []
    for row in ordered_rows[1:]:
        values = [entry.get("text", "") for entry in row]
        table_rows.append({header: values[index] if index < len(values) else None for index, header in enumerate(headers)})

    return [{"headers": headers, "rows": table_rows}]
