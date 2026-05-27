from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import current_app

from backend.models.database import Batch, Document, ExtractionResult, TableData, db
from backend.services.bbox_renderer import render_bounding_boxes
from backend.services.document_classifier import classify_document
from backend.services.field_extractor import normalize_extraction_results
from backend.services.helpers import confidence_from_score
from backend.services.image_preprocessor import preprocess_image
from backend.services.ocr_engine import extract_ocr, load_ocr_reader
from backend.services.pdf_processor import convert_pdf_to_images
from backend.services.table_extractor import extract_tables
from backend.services.vision_extractor import extract_with_schema


def _document_pages(document: Document) -> list[dict[str, Any]]:
    source_path = Path(document.original_path)
    if source_path.suffix.lower() == ".pdf":
        page_paths = convert_pdf_to_images(str(source_path), current_app.config["OUTPUT_FOLDER"])
        return [{"page_number": index + 1, "image_path": page_path} for index, page_path in enumerate(page_paths)]
    return [{"page_number": 1, "image_path": str(source_path)}]


def _load_reader():
    reader = current_app.config.get("OCR_READER")
    if reader is None:
        reader = load_ocr_reader()
        current_app.config["OCR_READER"] = reader
    return reader


def _merge_field_maps(field_maps: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field_map in field_maps:
        for key, value in field_map.items():
            if value is None or value == "" or value == []:
                continue
            if key not in merged or merged[key] is None or merged[key] == "" or merged[key] == []:
                merged[key] = value
    return merged


def _build_layout_context(ocr_words: list[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[int, list[dict[str, Any]]] = {}
    for word in ocr_words:
        bbox = word.get("bbox") or []
        y = int(bbox[1] // 30) if len(bbox) > 1 else 0
        rows.setdefault(y, []).append(
            {
                "text": word.get("text"),
                "confidence": word.get("confidence"),
                "bbox": bbox,
            }
        )

    ordered_rows = []
    for row_index in sorted(rows):
        ordered_rows.append(sorted(rows[row_index], key=lambda item: (item.get("bbox") or [0, 0, 0, 0])[0]))

    return {
        "rows": ordered_rows,
        "word_count": len(ocr_words),
        "bbox_words": [
            {
                "text": word.get("text"),
                "confidence": word.get("confidence"),
                "bbox": word.get("bbox"),
            }
            for word in ocr_words
        ],
    }


def _field_annotations_to_records(document_id: str, page_number: int, annotations: list[dict[str, Any]]) -> list[ExtractionResult]:
    records: list[ExtractionResult] = []
    for item in annotations:
        bbox = item.get("bbox") or []
        confidence_value = item.get("confidence_score")
        records.append(
            ExtractionResult(
                document_id=document_id,
                page_number=int(item.get("page_number", page_number)),
                field_name=item.get("field_name", "field"),
                field_value=item.get("field_value"),
                confidence=confidence_from_score(confidence_value if isinstance(confidence_value, (int, float)) else 0.35),
                bbox_x=bbox[0] if len(bbox) > 0 else None,
                bbox_y=bbox[1] if len(bbox) > 1 else None,
                bbox_w=bbox[2] if len(bbox) > 2 else None,
                bbox_h=bbox[3] if len(bbox) > 3 else None,
            )
        )
    return records


def process_document(document_id: str) -> dict[str, Any]:
    document = db.session.get(Document, document_id)
    if document is None:
        raise ValueError("Document not found")

    reader = _load_reader()
    pages = _document_pages(document)
    page_results: list[dict[str, Any]] = []
    page_field_maps: list[dict[str, Any]] = []
    page_field_annotations: list[dict[str, Any]] = []
    page_tables: list[dict[str, Any]] = []

    if not pages:
        raise ValueError("No pages available for document processing")

    classification = {"document_type": document.doc_type or "form", "confidence": float(document.classification_confidence or 0.35)}

    for index, page in enumerate(pages):
        preprocessing = preprocess_image({"image_path": page["image_path"]})
        processed_path = preprocessing.get("processed_path") or page["image_path"]
        ocr = extract_ocr({"processed_path": processed_path}, reader=reader)
        # Sort OCR blocks top-to-bottom, then left-to-right and assign block_index
        try:
            ocr_words = ocr.get("words", []) or []
            ocr_words_sorted = sorted(ocr_words, key=lambda b: (int((b.get("bbox") or [0,0,0,0])[1]) // 20, int((b.get("bbox") or [0,0,0,0])[0])))
            for idx, w in enumerate(ocr_words_sorted):
                w["block_index"] = idx
            ocr["words"] = ocr_words_sorted
        except Exception:
            pass

        layout_context = _build_layout_context(ocr.get("words", []))

        if index == 0:
            classification = classify_document(
                {
                    "image_path": processed_path,
                    "ocr_text": ocr.get("full_text", ""),
                    "document_type": document.doc_type,
                    "layout_context": layout_context,
                }
            )

        extracted_fields = extract_with_schema(
            {
                "image_path": processed_path,
                "ocr_text": ocr.get("full_text", ""),
                "document_type": classification.get("document_type"),
                "layout_context": layout_context,
            }
        )

        # Step: numeric casting and math validation (invoices/receipts)
        try:
            from backend.services.field_extractor import cast_and_validate_numbers, validate_and_heal, ensure_field_values

            extracted_fields = cast_and_validate_numbers(extracted_fields, classification.get("document_type"))
            # Ensure every field dict has a 'value' key before healing
            extracted_fields = ensure_field_values(extracted_fields)
            # Healing: attempt OCR-based recovery for missing required fields
            extracted_fields = validate_and_heal(extracted_fields, ocr, classification.get("document_type"))
        except Exception:
            # if validation/healing fails, continue with original extracted_fields
            pass

        annotations = normalize_extraction_results(extracted_fields, ocr.get("words", []))
        tables = extract_tables({"image_path": processed_path, "ocr_words": ocr.get("words", [])}).get("tables", [])
        page_annotations = [{**item, "page_number": page["page_number"]} for item in annotations]
        page_tables_with_page = [{**table, "page_number": page["page_number"]} for table in tables]

        page_field_maps.append(extracted_fields)
        page_field_annotations.extend(page_annotations)
        page_tables.extend(page_tables_with_page)
        page_results.append(
            {
                "page_number": page["page_number"],
                "original_path": page["image_path"],
                "processed_path": processed_path,
                "preprocessing": preprocessing,
                "ocr": ocr,
                "layout_context": layout_context,
                "fields": extracted_fields,
                "field_annotations": page_annotations,
                "tables": page_tables_with_page,
            }
        )

        if index == 0:
            document.preprocessed_path = processed_path

    merged_fields = _merge_field_maps(page_field_maps)

    # Keep SQLite writes short-lived: remove and replace related rows only after all OCR/LLM work is done.
    db.session.query(ExtractionResult).filter_by(document_id=document.id).delete(synchronize_session=False)
    db.session.query(TableData).filter_by(document_id=document.id).delete(synchronize_session=False)

    for record in _field_annotations_to_records(document.id, 1, page_field_annotations):
        db.session.add(record)

    for table_index, table in enumerate(page_tables):
        db.session.add(
            TableData(
                document_id=document.id,
                page_number=int(table.get("page_number", 1)),
                table_index=table_index,
                headers=table.get("headers", []),
                rows=table.get("rows", []),
            )
        )

    preview_source = page_results[0]["processed_path"] if page_results else document.original_path
    document.preview_path = render_bounding_boxes(preview_source, page_field_annotations)
    document.doc_type = classification.get("document_type")
    document.classification_confidence = float(classification.get("confidence", 0.35) or 0.35)
    document.page_count = len(pages)
    document.status = "processed"
    document.extraction_result = {
        "document_id": document.id,
        "classification": {
            "type": document.doc_type,
            "confidence": document.classification_confidence,
        },
        "fields": merged_fields,
        "field_annotations": page_field_annotations,
        "tables": page_tables,
        "ocr": {
            "full_text": "\n".join([str((page_result.get("ocr") or {}).get("full_text") or "").strip() for page_result in page_results]).strip(),
            "pages": [page_result["ocr"] for page_result in page_results],
        },
        "layout_context": [page_result.get("layout_context") for page_result in page_results],
        "pages": page_results,
        "status": document.status,
    }

    db.session.commit()

    return document.extraction_result


def process_batch_documents(document_ids: list[str], batch_id: str | None = None) -> dict[str, Any]:
    documents = Document.query.filter(Document.id.in_(document_ids)).all()
    if not documents:
        raise ValueError("No documents found")

    if batch_id:
        batch_record = db.session.get(Batch, batch_id)
        if batch_record is not None:
            batch_record.total = len(documents)
            batch_record.processed = 0
            batch_record.successful = 0
            batch_record.failed = 0
            batch_record.status = "running"
            if not batch_record.document_ids:
                batch_record.document_ids = list(document_ids)
            db.session.commit()

    results: list[dict[str, Any]] = []
    processed = 0
    successful = 0
    failed = 0

    for document in documents:
        processed += 1
        try:
            results.append(process_document(document.id))
            successful += 1
        except Exception as exc:
            failed += 1
            results.append({"document_id": document.id, "error": str(exc)})

        if batch_id:
            batch_record = db.session.get(Batch, batch_id)
            if batch_record is not None:
                batch_record.processed = processed
                batch_record.successful = successful
                batch_record.failed = failed
                batch_record.status = "running" if processed < len(documents) else ("done" if failed == 0 else "failed")
                db.session.commit()

    final_status = "done" if failed == 0 else "failed"
    if batch_id:
        batch_record = db.session.get(Batch, batch_id)
        if batch_record is not None:
            batch_record.total = len(documents)
            batch_record.processed = processed
            batch_record.successful = successful
            batch_record.failed = failed
            batch_record.status = final_status
            if not batch_record.document_ids:
                batch_record.document_ids = list(document_ids)
            db.session.commit()

    return {
        "results": results,
        "processed": processed,
        "successful": successful,
        "failed": failed,
        "status": final_status,
    }
