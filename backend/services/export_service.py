from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

from openpyxl import Workbook


def build_document_payload(document: Any, extraction_results: list[dict] | None = None, tables: list[dict] | None = None) -> dict:
    return {
        "document": document.to_dict() if hasattr(document, "to_dict") else document,
        "fields": extraction_results or [],
        "tables": tables or [],
    }


def export_json_file(payload: dict, output_path: str) -> str:
    path = Path(output_path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def export_csv_file(fields: list[dict], output_path: str) -> str:
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field_name", "field_value", "confidence"])
        writer.writeheader()
        for item in fields:
            writer.writerow({"field_name": item.get("field_name"), "field_value": item.get("field_value"), "confidence": item.get("confidence")})
    return str(path)


def export_excel_file(payload: dict, output_path: str) -> str:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet.append(["Field", "Value"])
    for key, value in payload.get("document", {}).items():
        summary_sheet.append([key, value])

    fields_sheet = workbook.create_sheet("Fields")
    fields_sheet.append(["Field", "Value", "Confidence"])
    for item in payload.get("fields", []):
        fields_sheet.append([item.get("field_name"), item.get("field_value"), item.get("confidence")])

    tables_sheet = workbook.create_sheet("Tables")
    tables_sheet.append(["Table Index", "Headers", "Rows"])
    for index, table in enumerate(payload.get("tables", []), start=1):
        tables_sheet.append([index, json.dumps(table.get("headers", [])), json.dumps(table.get("rows", []))])

    workbook.save(output_path)
    return output_path


def export_batch_zip(files: list[str], output_zip_path: str) -> str:
    path = Path(output_zip_path)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=Path(file_path).name)
    return str(path)
