"""Deterministic text built from engine output. Also the safe fallback when no AI explanation is available."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.models import ReceiptInput, Status

if TYPE_CHECKING:
    from app.engine.models import ValidationResult


def _fmt(n: int) -> str:
    return f"{n:,}"


def summarise(r: ValidationResult, receipt: ReceiptInput) -> str:
    rule = r.matched_rule
    if r.status is Status.NEEDS_MANUAL_REVIEW:
        return f"A person needs to review this case. {r.manual_reason}"
    if r.status is Status.INVALID_REASON_MISMATCH:
        return (f"The cited Section {r.cited_rule.section} does not match the offence described. "
                f"The reason points to Section {rule.section}.")
    if r.status is Status.INVALID_FINE_TOO_HIGH:
        return (f"Section {rule.section} ({rule.title}) applies. The fine of Tk {_fmt(receipt.amount)} is above the "
                f"allowed Tk {_fmt(r.allowed_fine)}.")
    if r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE:
        return (f"Section {rule.section} ({rule.title}) applies and the amount is within limits, but an exemption may "
                "excuse the offence entirely if the evidence is shown.")
    if r.status is Status.INVALID_EXCEPTION_NOT_APPLICABLE:
        return (f"Section {rule.section} applies and the amount is within limits. The exception that was claimed does "
                "not apply to this offence.")
    return (f"Section {rule.section} ({rule.title}) applies and the fine of Tk {_fmt(receipt.amount)} is within the "
            f"allowed Tk {_fmt(r.allowed_fine)}.")


def explain(r: ValidationResult, receipt: ReceiptInput) -> str:
    text = r.summary or summarise(r, receipt)
    if r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE:
        e = next(x for x in r.exceptions if x.applies)
        text += f" The relevant provision is {e.source_reference}. {e.scope_limit}"
    if r.status is Status.INVALID_EXCEPTION_NOT_APPLICABLE:
        e = next(x for x in r.exceptions if x.claimed and not x.applies)
        text += f" {e.scope_limit}"
    return text
