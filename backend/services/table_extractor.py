from __future__ import annotations

from collections import defaultdict
from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


from backend.services.helpers import normalize_bbox


def _normalize_bbox(bbox: Any) -> list[int]:
    norm = normalize_bbox(bbox)
    if norm is None:
        return [0, 0, 0, 0]
    return norm


def extract_tables(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    ocr_words = payload.get("ocr_words") or []
    if not ocr_words:
        return {"tables": []}
    # Locate the table region by scanning for header row and subtotal/end marker
    header_keywords = {"description", "quantity", "rate", "amount"}
    table_start_y = None
    table_end_y = None
    for item in ocr_words:
        text = str(item.get("text", "") or "").lower()
        words = set([w.strip(" ,:\t") for w in text.split() if w.strip()])
        if header_keywords.issubset(words) and table_start_y is None:
            bbox = item.get("bbox") or []
            norm = _normalize_bbox(bbox)
            table_start_y = norm[1]
        if "sub" in text and "total" in text and table_start_y is not None and table_end_y is None:
            bbox = item.get("bbox") or []
            norm = _normalize_bbox(bbox)
            table_end_y = norm[1]

    if table_start_y is None or table_end_y is None or table_end_y <= table_start_y:
        return {"tables": []}

    # Collect blocks within the table region
    blocks_in_table = [item for item in ocr_words if isinstance(item.get("bbox"), (list, tuple)) and table_start_y <= _normalize_bbox(item.get("bbox"))[1] <= table_end_y]
    if not blocks_in_table:
        return {"tables": []}

    def detect_column_bands(blocks_in_table, gap_threshold=40):
        x_centers = sorted([((b["bbox"][0] + b["bbox"][2]) // 2) for b in blocks_in_table])
        bands = []
        if not x_centers:
            return bands
        current_band = [x_centers[0]]
        for x in x_centers[1:]:
            if x - current_band[-1] > gap_threshold:
                bands.append((min(current_band), max(current_band)))
                current_band = [x]
            else:
                current_band.append(x)
        bands.append((min(current_band), max(current_band)))
        return bands

    bands = detect_column_bands(blocks_in_table)
    if not bands:
        return {"tables": []}

    # assign block to nearest band
    def assign_band(block, bands):
        x0, x2 = _normalize_bbox(block.get("bbox"))[:2] + _normalize_bbox(block.get("bbox"))[2:4]
        x_center = (x0 + x2) // 2
        best = None
        best_dist = None
        for idx, (l, r) in enumerate(bands):
            center = (l + r) // 2
            dist = abs(x_center - center)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = idx
        return best

    # group into rows by y-bin
    rows = {}
    for b in blocks_in_table:
        y_top = _normalize_bbox(b.get("bbox"))[1]
        row_key = y_top // 15
        rows.setdefault(row_key, []).append(b)

    ordered_row_keys = sorted(rows.keys())
    # Build header and data rows
    header_row = None
    data_rows = []
    for i, key in enumerate(ordered_row_keys):
        row_blocks = rows[key]
        # sort blocks by x
        row_blocks_sorted = sorted(row_blocks, key=lambda entry: _normalize_bbox(entry.get("bbox"))[0])
        # for header detection, check if this row contains all header keywords
        row_text = " ".join([str(b.get("text", "")).lower() for b in row_blocks_sorted])
        if header_row is None and header_keywords.issubset(set(row_text.split())):
            header_row = row_blocks_sorted
            continue
        if header_row is not None:
            # stop if we reach subtotal marker
            if any("sub" in str(b.get("text", "")).lower() and "total" in str(b.get("text", "")).lower() for b in row_blocks_sorted):
                break
            data_rows.append(row_blocks_sorted)

    if not header_row:
        return {"tables": []}

    # Determine headers by their texts in header_row
    headers = [str(b.get("text", "")).strip() for b in header_row]

    # For each data row, map blocks into header columns via nearest band center
    table_rows = []
    for row in data_rows:
        # create empty cells
        cells = [None] * len(headers)
        for block in row:
            x_center = ((_normalize_bbox(block.get("bbox"))[0] + _normalize_bbox(block.get("bbox"))[2]) // 2)
            # find nearest header index by x position
            best_idx = None
            best_dist = None
            header_centers = [((_normalize_bbox(h.get("bbox"))[0] + _normalize_bbox(h.get("bbox"))[2]) // 2) if isinstance(h.get("bbox"), list) else idx*100 for idx, h in enumerate(header_row)]
            for idx_h, hc in enumerate(header_centers):
                dist = abs(x_center - hc)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_idx = idx_h
            if best_idx is not None:
                if cells[best_idx]:
                    cells[best_idx] += " " + str(block.get("text", ""))
                else:
                    cells[best_idx] = str(block.get("text", ""))
        table_rows.append([cell if cell is not None else "" for cell in cells])

    return {"tables": [{"headers": headers, "rows": table_rows}]}
