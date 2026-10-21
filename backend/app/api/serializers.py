"""Build API responses from database rows."""

from __future__ import annotations

from typing import Any

from app import models
from app.schemas import CaseListItem, FieldReading, ReadingOut


def case_list_item(c: models.MamlaCase) -> CaseListItem:
    return CaseListItem(
        id=c.id, created_at=c.created_at, case_source=c.case_source, validation_status=c.validation_status,
        reason=c.extracted_reason, amount=c.extracted_amount,
        section=c.matched_rule.section_number if c.matched_rule else None,
        confidence=float(c.confidence_score) if c.confidence_score is not None else None,
        receipt_number=c.extracted_receipt_number, location=c.extracted_location, dummy_url=c.dummy_url,
    )


def case_detail(c: models.MamlaCase) -> dict[str, Any]:
    rule = c.matched_rule
    return {
        "id": str(c.id),
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "case_source": c.case_source,
        "dummy_url": c.dummy_url,
        "validation_status": c.validation_status,
        "validation_summary": c.validation_summary,
        "ai_explanation": c.ai_explanation,
        "confidence_score": float(c.confidence_score) if c.confidence_score is not None else None,
        "extracted": {
            "reason": c.extracted_reason, "amount": c.extracted_amount,
            "date": c.extracted_date.isoformat() if c.extracted_date else None,
            "location": c.extracted_location, "vehicle_type": c.extracted_vehicle_type,
            "receipt_number": c.extracted_receipt_number, "section": c.extracted_section, "notes": c.claim_notes,
        },
        "manual_input": c.manual_input or {},
        "receipt": (
            {"id": str(c.receipt.id), "file_name": c.receipt.file_name, "file_type": c.receipt.file_type,
             "file_hash": c.receipt.file_hash, "reading_status": c.receipt.extraction_status,
             "text_read": c.receipt.raw_ocr_text, "reading_model": (c.receipt.extraction or {}).get("model"),
             "reading": reading_out(c.receipt).model_dump()}
            if c.receipt else None
        ),
        "dataset": (
            {"id": str(c.dataset_version.id), "name": c.dataset_version.version_name} if c.dataset_version else None
        ),
        "matched_rule": (
            {"id": str(rule.id), "section": rule.section_number, "title": rule.offence_title,
             "category": rule.offence_category, "min_fine": rule.min_fine, "max_fine": rule.max_fine,
             "fine_text": rule.fine_text, "imprisonment_text": rule.imprisonment_text,
             "source_reference": rule.source_reference}
            if rule else None
        ),
        "matches": [
            {"section": m.rule.section_number, "title": m.rule.offence_title, "score": m.match_score,
             "reason": m.match_reason}
            for m in c.matches
        ],
        "exception_checks": [
            {"key": e.rule.rule_key, "title": e.rule.exception_title, "applies": e.applies, "reason": e.reason,
             "source_reference": e.rule.source_reference}
            for e in c.exception_checks
        ],
        "analysis": c.analysis_details,
        "audit": audit_summary(c),
    }


def reading_out(receipt: models.UploadedReceipt, message: str | None = None) -> ReadingOut:
    ex = receipt.extraction or {}
    return ReadingOut(
        status=receipt.extraction_status or "pending", message=message, language=ex.get("language"), legible=ex.get("legible"),
        fields={k: FieldReading(**v) for k, v in (ex.get("fields") or {}).items()},
    )


def audit_summary(c: models.MamlaCase) -> dict[str, Any]:
    """What is recorded for a case, from the database only. Use /verify to compare it with the blockchain."""
    from app.services import sealing

    latest = sealing.latest_record(c)
    from app.core.config import get_settings

    return {
        "enabled": get_settings().blockchain_enabled,
        "status": latest.status if latest else "not_recorded",
        "latest": sealing.history(c)[-1] if latest else None,
        "records": len(c.records),
    }
