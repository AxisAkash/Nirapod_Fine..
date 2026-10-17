"""Deterministic validation: select the offence, check the fine, check exceptions, pick one status."""

from __future__ import annotations

from collections.abc import Sequence

from app.engine.exceptions import check_exceptions
from app.engine.explanation import summarise
from app.engine.models import (
    Candidate,
    Dataset,
    FineTier,
    Justification,
    OffenceRule,
    PriorCase,
    ReceiptInput,
    Status,
    ValidationResult,
)
from app.engine.normalize import contains, normalize, parse_section
from app.engine.retrieval import rank_candidates, section_matches

MIN_REASON_SCORE = 30  # reason evidence needed before a section can be selected
TIE_MARGIN = 5  # top two reason scores closer than this are treated as ambiguous


def _fmt(n: int) -> str:
    return f"{n:,}"


def _select(
    ranked: list[Candidate], cited: str | None, dataset: Dataset
) -> tuple[Candidate | None, OffenceRule | None, bool, str | None]:
    """Return (matched, cited_rule, mismatch, manual_reason)."""
    by_reason = sorted(ranked, key=lambda c: c.reason_score, reverse=True)
    best, second = by_reason[0], by_reason[1]
    if cited:
        cited_candidates = sorted(
            (c for c in ranked if section_matches(cited, c.rule)),
            key=lambda c: c.reason_score,
            reverse=True,
        )
        if not cited_candidates:
            existing = next((r for r in dataset.rules if section_matches(cited, r)), None)
            if existing:
                return (
                    None,
                    existing,
                    False,
                    f"Section {existing.section} is a supporting provision and cannot be checked as an offence.",
                )
            return None, None, False, f"The receipt cites Section {cited}, which is not in the active dataset."
        c = cited_candidates[0]
        if c.reason_score >= MIN_REASON_SCORE:
            return c, c.rule, False, None
        if best.reason_score >= MIN_REASON_SCORE and best.rule is not c.rule:
            return best, c.rule, True, None
        return (
            None,
            c.rule,
            False,
            f"The receipt cites Section {c.rule.section} but the offence reason does not clearly support it.",
        )
    if best.reason_score >= MIN_REASON_SCORE:
        if best.reason_score - second.reason_score >= TIE_MARGIN:
            return best, None, False, None
        return (
            None,
            None,
            False,
            f"Two sections score almost equally ({best.rule.section} and {second.rule.section}), "
            "so the offence is ambiguous.",
        )
    return None, None, False, "No section in the dataset matches the offence reason closely enough."


def _pick_tier(rule: OffenceRule, receipt: ReceiptInput) -> tuple[FineTier | None, bool]:
    """Pick the fine tier the receipt describes. Returns (tier, undecided)."""
    if not rule.fine_tiers:
        return None, False
    text_n = normalize(f"{receipt.reason} {receipt.notes or ''}")
    hits = [t for t in rule.fine_tiers if any(contains(text_n, k) for k in t.keywords)]
    if len(hits) == 1:
        return hits[0], False
    return None, True


def validate(receipt: ReceiptInput, dataset: Dataset, history: Sequence[PriorCase] = ()) -> ValidationResult:
    cited = parse_section(receipt.section)
    amount = receipt.amount
    ranked = rank_candidates(receipt.reason, amount, cited, dataset)
    matched, cited_rule, mismatch, manual = _select(ranked, cited, dataset)
    rule = matched.rule if matched else None

    confidence = 0
    if matched:
        confidence = min(99, matched.reason_score + (10 if cited_rule is rule else 0))

    # ---- ceiling, tier and repeat history ----------------------------------------------------------
    allowed = allowed_low = previous = None
    max_fine = None
    tier = None
    undecided_tier = False
    occurrence = 1
    if rule and rule.max_fine is not None:
        tier, undecided_tier = _pick_tier(rule, receipt)
        max_fine = tier.max_fine if tier else rule.max_fine
        prior = sorted(
            (h for h in history if h.section == rule.section and h.occurred_at < receipt.checked_at),
            key=lambda h: h.occurred_at,
            reverse=True,
        )
        occurrence = len(prior) + 1
        cap = prior[0].amount * 2 if prior else None
        previous = prior[0].amount if prior else None
        allowed = min(cap, max_fine) if cap is not None else max_fine
        if undecided_tier:
            low = min(t.max_fine for t in rule.fine_tiers)
            allowed_low = min(cap, low) if cap is not None else low

    if rule and not manual and not mismatch:
        if amount is None:
            manual = "No fine amount was found on the receipt."
        elif rule.max_fine is None:
            manual = (
                f"Section {rule.section} has no Taka ceiling in the source data, so the amount cannot be "
                "checked automatically."
            )
        elif amount < rule.min_fine:
            manual = f"The amount is below the statutory minimum of Tk {_fmt(rule.min_fine)} for Section {rule.section}."
        elif undecided_tier and allowed is not None and allowed_low is not None and allowed_low < amount <= allowed:
            lowest = min(rule.fine_tiers, key=lambda t: t.max_fine)
            manual = (
                f"Section {rule.section} has a lower ceiling of Tk {_fmt(lowest.max_fine)} for a {lowest.label}. "
                f"The receipt does not say which kind applies, and Tk {_fmt(amount)} is above that lower ceiling."
            )

    # ---- exceptions -----------------------------------------------------------------------------------
    exceptions = check_exceptions(receipt, rule, dataset) if rule else []
    any_applies = any(e.applies for e in exceptions)
    bad_claim = any(e.claimed and not e.applies for e in exceptions)
    too_high = amount is not None and allowed is not None and amount > allowed

    # ---- status precedence: first true row wins ------------------------------------------------------
    if manual:
        status = Status.NEEDS_MANUAL_REVIEW
    elif mismatch:
        status = Status.INVALID_REASON_MISMATCH
    elif too_high:
        status = Status.INVALID_FINE_TOO_HIGH
    elif any_applies:
        status = Status.VALID_BUT_EXCEPTION_POSSIBLE
    elif bad_claim:
        status = Status.INVALID_EXCEPTION_NOT_APPLICABLE
    else:
        status = Status.VALID

    flags: list[str] = []
    if rule and not manual and not mismatch and too_high and status is not Status.INVALID_FINE_TOO_HIGH:
        flags.append("Fine above allowed")
    if any_applies and status is not Status.VALID_BUT_EXCEPTION_POSSIBLE:
        flags.append("Exception possible")
    if bad_claim and status is not Status.INVALID_EXCEPTION_NOT_APPLICABLE:
        flags.append("Exception claim rejected")
    if previous is not None:
        flags.append("Repeat offence")
    if rule and rule.imprisonment_text:
        flags.append("Imprisonment also possible")

    result = ValidationResult(
        status=status,
        summary="",
        matched=matched,
        cited_rule=cited_rule,
        cited_section=cited,
        candidates=ranked[:5],
        confidence=confidence,
        max_fine=max_fine if max_fine is not None else (rule.max_fine if rule else None),
        allowed_fine=allowed,
        previous_fine=previous,
        occurrence=occurrence,
        exceptions=exceptions,
        justifications=[],
        flags=flags,
        manual_reason=manual,
        dataset_name=dataset.name,
        tier_label=tier.label if tier else None,
    )
    result.justifications = _justify(result, receipt, dataset, mismatch, ranked)
    result.summary = summarise(result, receipt)
    return result


def _justify(
    r: ValidationResult, receipt: ReceiptInput, dataset: Dataset, mismatch: bool, ranked: list[Candidate]
) -> list[Justification]:
    out: list[Justification] = []
    rule, amount = r.matched_rule, receipt.amount
    if r.matched and rule:
        signals = " · ".join(w for w in r.matched.why if "amount" not in w)
        if mismatch and r.cited_rule:
            out.append(
                Justification(
                    "bad",
                    f"Reason points to Section {rule.section}, not Section {r.cited_rule.section}",
                    f"The receipt cites Section {r.cited_rule.section} ({r.cited_rule.title}), but the offence reason "
                    f"matches Section {rule.section} ({rule.title}).",
                    signals,
                )
            )
        else:
            out.append(
                Justification(
                    "ok", f"Section {rule.section}: {rule.title}", f"Matched with {r.confidence}% confidence.", signals
                )
            )
    else:
        best = max((c.reason_score for c in ranked), default=0)
        out.append(
            Justification(
                "warn",
                "No reliable section match",
                r.manual_reason or "",
                f"best reason score {best}, threshold {MIN_REASON_SCORE}",
            )
        )
    if rule and not mismatch:
        tier_note = f" ({r.tier_label})" if r.tier_label else ""
        if r.manual_reason and r.matched:
            out.append(
                Justification(
                    "warn",
                    "Amount cannot be checked automatically",
                    r.manual_reason,
                    f"max_fine = {rule.max_fine}, min_fine = {rule.min_fine}",
                )
            )
        elif r.allowed_fine is not None and amount is not None:
            over = amount - r.allowed_fine
            basis = (
                "allowed_fine = min(previous × 2, max_fine)"
                if r.previous_fine is not None
                else "allowed_fine = max_fine"
            )
            if over > 0:
                if r.previous_fine is not None:
                    text = (
                        f"This is occurrence {r.occurrence} of Section {rule.section}. The previous fine was "
                        f"Tk {_fmt(r.previous_fine)}, so at most min({_fmt(r.previous_fine)} × 2, "
                        f"{_fmt(r.max_fine)}){tier_note} = Tk {_fmt(r.allowed_fine)} is allowed. "
                        f"Tk {_fmt(amount)} is charged, Tk {_fmt(over)} over."
                    )
                else:
                    text = (
                        f"Section {rule.section} allows up to Tk {_fmt(r.max_fine)}{tier_note}. "
                        f"Tk {_fmt(amount)} is charged, Tk {_fmt(over)} over."
                    )
                out.append(Justification("bad", "Fine exceeds the allowed amount", text, f"{basis} = {r.allowed_fine}"))
            else:
                if r.previous_fine is not None:
                    text = (
                        f"Repeat offence: allowed Tk {_fmt(r.allowed_fine)} (previous Tk {_fmt(r.previous_fine)} "
                        f"doubled, capped at Tk {_fmt(r.max_fine)}{tier_note}). Charged Tk {_fmt(amount)}."
                    )
                else:
                    text = (
                        f"First recorded offence under this section. Charged Tk {_fmt(amount)} against a maximum of "
                        f"Tk {_fmt(r.max_fine)}{tier_note}."
                    )
                out.append(
                    Justification("ok", "Fine is within the allowed amount", text, f"{basis} = {r.allowed_fine}")
                )
    if rule:
        if not r.exceptions:
            out.append(
                Justification(
                    "ok",
                    "No exception applies",
                    "No emergency, permit or special-vehicle claim was found, and the vehicle type triggers none of "
                    f"the {len(dataset.exceptions)} exception rules.",
                    f"{len(dataset.exceptions)} exception rules evaluated",
                )
            )
        for e in r.exceptions:
            if e.applies:
                tone, lead = "warn", "Exception possible: "
            elif e.informational:
                tone, lead = "info", "Checked, not applicable: "
            else:
                tone, lead = "bad", "Exception claim rejected: "
            out.append(Justification(tone, lead + e.title, e.reason, e.source_reference))
        if rule.imprisonment_text:
            out.append(Justification("info", "Imprisonment may also apply", rule.imprisonment_text, rule.source_reference))
    return out
