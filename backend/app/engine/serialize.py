"""Turn engine results into plain JSON-safe dicts (stored on the case and returned by the API)."""

from __future__ import annotations

from typing import Any

from app.engine.models import Candidate, ExceptionCheck, Justification, ValidationResult


def _candidate(c: Candidate) -> dict[str, Any]:
    return {
        "section": c.rule.section,
        "title": c.rule.title,
        "category": c.rule.category,
        "reason_score": c.reason_score,
        "section_score": c.section_score,
        "amount_score": c.amount_score,
        "total": c.total,
        "why": c.why,
    }


def _exception(e: ExceptionCheck) -> dict[str, Any]:
    return {
        "key": e.key,
        "title": e.title,
        "effect": e.effect,
        "source_reference": e.source_reference,
        "scope_limit": e.scope_limit,
        "required_evidence": e.required_evidence,
        "claimed": e.claimed,
        "applies": e.applies,
        "informational": e.informational,
        "reason": e.reason,
    }


def _justification(j: Justification) -> dict[str, Any]:
    return {"tone": j.tone, "title": j.title, "text": j.text, "meta": j.meta, "kind": j.kind}


def result_to_dict(r: ValidationResult) -> dict[str, Any]:
    rule = r.matched_rule
    return {
        "status": r.status.value,
        "summary": r.summary,
        "confidence": r.confidence,
        "matched_section": rule.section if rule else None,
        "matched_title": rule.title if rule else None,
        "matched_category": rule.category if rule else None,
        "cited_section": r.cited_section,
        "cited_rule_section": r.cited_rule.section if r.cited_rule else None,
        "statutory_max": r.max_fine,
        "statutory_min": rule.min_fine if rule else None,
        "fine_text": rule.fine_text if rule else None,
        "tier": r.tier_label,
        "allowed_fine": r.allowed_fine,
        "previous_fine": r.previous_fine,
        "occurrence": r.occurrence,
        "flags": r.flags,
        "manual_reason": r.manual_reason,
        "dataset": r.dataset_name,
        "candidates": [_candidate(c) for c in r.candidates],
        "exceptions": [_exception(e) for e in r.exceptions],
        "justifications": [_justification(j) for j in r.justifications],
    }
