"""Create and analyse cases: run the engine on the active dataset and persist every part of the result."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.engine import PriorCase, ReceiptInput, Status, explain, validate
from app.engine.serialize import result_to_dict
from app.services import explainer, integrity, sealing
from app.services.datasets import get_active_version, load_engine_dataset
from app.services.extraction import extract_fields
from app.services.parsing import parse_amount, parse_date

PENDING = "PENDING_ANALYSIS"
FIELDS = ("reason", "amount", "section", "vehicle", "notes", "date", "location", "receipt_number")
# A fine counts toward the repeat-offence history when the amount itself was within the allowed limit.
COUNTS_AS_HISTORY = {Status.VALID, Status.VALID_BUT_EXCEPTION_POSSIBLE, Status.INVALID_EXCEPTION_NOT_APPLICABLE}


class AnalysisError(Exception):
    pass


class DatasetIntegrityError(AnalysisError):
    """The legal rules in the database no longer match what was recorded on the blockchain."""


def _clean(fields: dict[str, Any]) -> dict[str, Any]:
    """Keep what the user sent. An empty string is kept on purpose: it means "this field is blank", which must
    override a value the AI read from the receipt. Only fields that were not sent at all (None) are dropped."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in fields.items() if k in FIELDS and v is not None}


def create_case(
    db: Session,
    user: models.User,
    source: str,
    fields: dict[str, Any],
    receipt: models.UploadedReceipt | None = None,
    dummy_url: str | None = None,
) -> models.MamlaCase:
    case = models.MamlaCase(
        user_id=user.id, receipt_id=receipt.id if receipt else None, case_source=source, dummy_url=dummy_url,
        manual_input=_clean(fields), validation_status=PENDING,
    )
    db.add(case)
    db.flush()
    return case


def analyze_case(db: Session, case: models.MamlaCase, overrides: dict[str, Any] | None = None) -> models.MamlaCase:
    """Run the engine and replace every stored result for this case. Safe to call again on the same case."""
    version = get_active_version(db)
    if version is None:
        raise AnalysisError("No active dataset version. Run `python -m app.seed` first.")
    if overrides:
        case.manual_input = {**(case.manual_input or {}), **_clean(overrides)}
    fields = {**extract_fields(case.receipt), **(case.manual_input or {})}
    check = integrity.check_dataset(db, version)
    if check.status == "tampered":
        raise DatasetIntegrityError(f"The legal dataset failed its integrity check, so no result was produced. {check.message}")
    loaded = load_engine_dataset(db, version)

    prior_rows = db.scalars(
        select(models.MamlaHistory).where(
            models.MamlaHistory.user_id == case.user_id, models.MamlaHistory.mamla_case_id != case.id,
            models.MamlaHistory.occurred_at < case.created_at,
        )
    ).all()
    history = [PriorCase(h.section_number, h.fine_amount, h.occurred_at) for h in prior_rows]

    receipt = ReceiptInput(
        reason=str(fields.get("reason") or ""), amount=parse_amount(fields.get("amount")),
        section=fields.get("section") or None, vehicle=fields.get("vehicle") or None, notes=fields.get("notes") or None,
        date=fields.get("date") or None, location=fields.get("location") or None,
        receipt_number=fields.get("receipt_number") or None, checked_at=case.created_at,
    )
    result = validate(receipt, loaded.dataset, history)

    # replace earlier results of this case
    db.execute(delete(models.MamlaCaseMatch).where(models.MamlaCaseMatch.mamla_case_id == case.id))
    db.execute(delete(models.MamlaExceptionCheck).where(models.MamlaExceptionCheck.mamla_case_id == case.id))
    db.execute(delete(models.MamlaHistory).where(models.MamlaHistory.mamla_case_id == case.id))
    db.expire(case, ["matches", "exception_checks"])

    for c in result.candidates:
        if c.total > 0:
            db.add(models.MamlaCaseMatch(
                mamla_case_id=case.id, offence_rule_id=loaded.rule_ids[c.rule.section],
                match_score=c.total, match_reason=" · ".join(c.why),
            ))
    for e in result.exceptions:
        db.add(models.MamlaExceptionCheck(
            mamla_case_id=case.id, exception_rule_id=loaded.exception_ids[e.key], applies=e.applies, reason=e.reason,
        ))

    matched = result.matched_rule
    case.dataset_version_id = version.id
    case.matched_offence_rule_id = loaded.rule_ids[matched.section] if matched else None
    case.validation_status = result.status.value
    case.validation_summary = result.summary
    details = result_to_dict(result)
    explanation = explainer.explain(details, receipt.amount, template=explain(result, receipt))
    details["explanation"] = {"source": explanation.source, "model": explanation.model, "note": explanation.note}
    details["dataset_integrity"] = {"status": check.status, "message": check.message}
    if check.status in {"unanchored", "unchecked"}:
        details["flags"] = [*details["flags"], "Dataset integrity could not be checked"]
    case.ai_explanation = explanation.text
    case.confidence_score = result.confidence
    case.extracted_reason = receipt.reason or None
    case.extracted_amount = receipt.amount
    case.extracted_date = parse_date(receipt.date)
    case.extracted_location = receipt.location
    case.extracted_vehicle_type = receipt.vehicle
    case.extracted_receipt_number = receipt.receipt_number
    case.extracted_section = receipt.section
    case.claim_notes = receipt.notes
    case.analysis_details = details

    if matched and result.status in COUNTS_AS_HISTORY and receipt.amount is not None:
        db.add(models.MamlaHistory(
            user_id=case.user_id, offence_rule_id=loaded.rule_ids[matched.section], mamla_case_id=case.id,
            fine_amount=receipt.amount, occurrence_number=result.occurrence, section_number=matched.section,
            occurred_at=case.created_at,
        ))
    db.commit()
    sealing.seal_quietly(db, case)  # record it on the blockchain; never fails the analysis
    db.refresh(case)
    return case
