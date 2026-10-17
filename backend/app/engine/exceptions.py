"""Exception and exemption checks. Every exception is bounded by its own scope limit."""
from __future__ import annotations

from app.engine.models import Dataset, ExceptionCheck, ExceptionRule, OffenceRule, ReceiptInput
from app.engine.normalize import contains, normalize

CLAIM_THRESHOLD = 15  # summed keyword weight at which receipt text counts as an explicit claim


def _in_scope(rule: ExceptionRule, offence: OffenceRule) -> bool:
    if rule.category == "*":
        return True
    if rule.section:
        return rule.section == offence.section
    return rule.category == offence.category


def check_exceptions(receipt: ReceiptInput, offence: OffenceRule, dataset: Dataset) -> list[ExceptionCheck]:
    text_n = normalize(f"{receipt.reason} {receipt.notes or ''}")
    vehicle_n = normalize(receipt.vehicle)
    checks: list[ExceptionCheck] = []
    for rule in dataset.exceptions:
        hits = [k for k in rule.keywords if contains(text_n, k.word)]
        claimed = sum(k.weight for k in hits) >= CLAIM_THRESHOLD
        vehicle_fit = bool(vehicle_n) and any(contains(vehicle_n, v) for v in rule.vehicles)
        if not claimed and not vehicle_fit:
            continue
        in_scope = _in_scope(rule, offence)
        words = ", ".join(k.word for k in hits)
        applies, info = False, False
        if rule.effect == "no_general_exemption":
            if not claimed:
                continue
            reason = (f"Claim detected ({words}). The sources do not establish a general exemption for this, "
                      f"so it does not excuse Section {offence.section}.")
        elif rule.effect == "repealed":
            if not claimed:
                continue
            reason = "The claim relies on a repealed provision, which is not current law."
        elif in_scope and (vehicle_fit or claimed):
            applies = True
            lead = ("Possible, but only with prior permission or evidence. " if rule.effect == "permission_based"
                    else "The vehicle or claim fits and the exemption covers this offence category. ")
            reason = f"{lead}Evidence needed: {rule.required_evidence}"
        elif claimed:
            reason = f"Claim detected ({words}) but it is out of scope for Section {offence.section}. {rule.scope_limit}"
        else:
            info = True
            reason = (f"The vehicle type fits this exemption, but it covers a different offence category than "
                      f"Section {offence.section}. {rule.scope_limit}")
        checks.append(ExceptionCheck(
            key=rule.key, title=rule.title, effect=rule.effect, source_reference=rule.source_reference,
            scope_limit=rule.scope_limit, required_evidence=rule.required_evidence, claimed=claimed,
            applies=applies, informational=info, reason=reason,
        ))
    return checks
