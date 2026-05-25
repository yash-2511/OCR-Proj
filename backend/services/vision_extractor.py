from __future__ import annotations

from pathlib import Path

from backend.config import BASE_DIR
from backend.services.helpers import read_json_file
from backend.services.llm_client import get_llm_client


SCHEMA_DIR = BASE_DIR / "backend" / "extraction_schemas"


def load_schema(doc_type: str) -> dict:
    schema_path = SCHEMA_DIR / f"{doc_type}.json"
    if schema_path.exists():
        return read_json_file(schema_path)
    return {"doc_type": doc_type, "fields": [], "prompt_hint": ""}


def extract_with_schema(image_base64: str, doc_type: str) -> dict:
    schema = load_schema(doc_type)
    return get_llm_client().extract(image_base64=image_base64, schema=schema, doc_type=doc_type)
