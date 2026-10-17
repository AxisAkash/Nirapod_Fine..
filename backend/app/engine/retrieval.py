"""Rule-based retrieval: score every offence rule against a receipt. No embeddings, no model calls."""
from __future__ import annotations

from app.engine.models import Candidate, Dataset, OffenceRule
from app.engine.normalize import contains, normalize

EXACT_ALIAS = 40
PARTIAL_ALIAS = 30
TITLE_MATCH = 30
CITED_SECTION = 50
AMOUNT_IN_RANGE = 10
KEYWORD_CAP = 60


def section_matches(cited: str | None, rule: OffenceRule) -> bool:
    """A cited '89' matches both 89(1) and 89(2); a cited '89(1)' matches only that rule."""
    return bool(cited) and (rule.section == cited or rule.section.startswith(f"{cited}("))


def reason_score(reason_n: str, rule: OffenceRule) -> tuple[int, list[str]]:
    score, why = 0, []
    best, best_alias = 0, ""
    for alias in rule.aliases:
        alias_n = normalize(alias)
        if not alias_n:
            continue
        value = 0
        if reason_n == alias_n:
            value = EXACT_ALIAS
        elif contains(reason_n, alias_n) or (len(reason_n) >= 5 and reason_n in alias_n):
            value = PARTIAL_ALIAS
        if value > best:
            best, best_alias = value, alias
    if best:
        score += best
        why.append(f"{'exact' if best == EXACT_ALIAS else 'partial'} alias “{best_alias}” +{best}")
    hits = [(k.word, k.weight) for k in rule.keywords if contains(reason_n, k.word)]
    if hits:
        kw = min(sum(w for _, w in hits), KEYWORD_CAP)
        score += kw
        why.append("keywords " + ", ".join(f"{w} +{wt}" for w, wt in hits))
    if contains(reason_n, rule.title):
        score += TITLE_MATCH
        why.append(f"title match +{TITLE_MATCH}")
    return score, why


def rank_candidates(reason: str, amount: int | None, cited: str | None, dataset: Dataset) -> list[Candidate]:
    reason_n = normalize(reason)
    out: list[Candidate] = []
    for rule in dataset.rules:
        if not rule.matchable:
            continue
        rs, why = reason_score(reason_n, rule)
        sec = CITED_SECTION if section_matches(cited, rule) else 0
        amt = AMOUNT_IN_RANGE if (rule.max_fine is not None and amount is not None and amount <= rule.max_fine) else 0
        if sec:
            why = why + [f"cited section +{CITED_SECTION}"]
        if amt:
            why = why + [f"amount within range +{AMOUNT_IN_RANGE}"]
        out.append(Candidate(rule, rs, sec, amt, why))
    return sorted(out, key=lambda c: c.total, reverse=True)
