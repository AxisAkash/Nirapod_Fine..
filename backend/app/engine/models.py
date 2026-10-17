"""Plain data types for the decision engine. No database or framework imports live here."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Status(str, Enum):
    VALID = "VALID"
    INVALID_FINE_TOO_HIGH = "INVALID_FINE_TOO_HIGH"
    INVALID_REASON_MISMATCH = "INVALID_REASON_MISMATCH"
    VALID_BUT_EXCEPTION_POSSIBLE = "VALID_BUT_EXCEPTION_POSSIBLE"
    INVALID_EXCEPTION_NOT_APPLICABLE = "INVALID_EXCEPTION_NOT_APPLICABLE"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"


@dataclass(frozen=True)
class Keyword:
    word: str
    weight: int


@dataclass(frozen=True)
class FineTier:
    """A lower or higher ceiling that depends on a detail of the offence (e.g. temporary vs permanent)."""
    label: str
    max_fine: int
    keywords: tuple[str, ...] = ()


@dataclass
class OffenceRule:
    section: str
    title: str
    category: str
    min_fine: int = 0
    max_fine: int | None = None
    fine_text: str = ""
    imprisonment_text: str | None = None
    repeat_rule_text: str | None = None
    source_reference: str = ""
    aliases: list[str] = field(default_factory=list)
    keywords: list[Keyword] = field(default_factory=list)
    matchable: bool = True
    fine_tiers: list[FineTier] = field(default_factory=list)


@dataclass
class ExceptionRule:
    key: str
    title: str
    category: str  # offence category it covers, or "*" for any
    effect: str  # exempts | permission_based | no_general_exemption | repealed
    section: str | None = None
    description: str = ""
    vehicles: list[str] = field(default_factory=list)
    conditions_text: list[str] = field(default_factory=list)
    scope_limit: str = ""
    required_evidence: str = ""
    source_reference: str = ""
    keywords: list[Keyword] = field(default_factory=list)


@dataclass
class Dataset:
    name: str
    rules: list[OffenceRule]
    exceptions: list[ExceptionRule]

    def rule_for_section(self, section: str) -> OffenceRule | None:
        return next((r for r in self.rules if r.section == section), None)


@dataclass
class ReceiptInput:
    reason: str
    amount: int | None = None
    section: str | None = None
    vehicle: str | None = None
    notes: str | None = None
    date: str | None = None
    location: str | None = None
    receipt_number: str | None = None
    checked_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class PriorCase:
    """An earlier fine by the same user. The caller decides which past cases count as history."""
    section: str
    amount: int
    occurred_at: datetime


@dataclass
class Candidate:
    rule: OffenceRule
    reason_score: int
    section_score: int
    amount_score: int
    why: list[str]

    @property
    def total(self) -> int:
        return self.reason_score + self.section_score + self.amount_score


@dataclass
class ExceptionCheck:
    key: str
    title: str
    effect: str
    source_reference: str
    scope_limit: str
    required_evidence: str
    claimed: bool  # the driver or receipt explicitly claimed it
    applies: bool
    informational: bool  # vehicle fits but it covers a different offence; not a claim
    reason: str


@dataclass
class Justification:
    tone: str  # ok | bad | warn | info
    title: str
    text: str
    meta: str = ""
    kind: str = "check"  # "check" for section and amount findings, "exception" for exception findings


@dataclass
class ValidationResult:
    status: Status
    summary: str
    matched: Candidate | None
    cited_rule: OffenceRule | None
    cited_section: str | None
    candidates: list[Candidate]
    confidence: int
    max_fine: int | None
    allowed_fine: int | None
    previous_fine: int | None
    occurrence: int
    exceptions: list[ExceptionCheck]
    justifications: list[Justification]
    flags: list[str]
    manual_reason: str | None
    dataset_name: str
    tier_label: str | None = None

    @property
    def matched_rule(self) -> OffenceRule | None:
        return self.matched.rule if self.matched else None
