"""Request and response shapes for the HTTP API."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManualFields(BaseModel):
    """Receipt fields typed by the user. They override anything read from the receipt image."""

    reason: str | None = None
    amount: int | str | None = None
    section: str | None = None
    vehicle: str | None = None
    notes: str | None = Field(default=None, description="Notes or an exception claimed by the driver")
    date: str | None = None
    location: str | None = None
    receipt_number: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str | None
    full_name: str | None
    role: str


class CaseListItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    case_source: str
    validation_status: str
    reason: str | None
    amount: int | None
    section: str | None
    confidence: float | None
    receipt_number: str | None = None
    location: str | None = None
    dummy_url: str | None = None


class CaseList(BaseModel):
    items: list[CaseListItem]
    total: int


class UploadOut(BaseModel):
    receipt_id: uuid.UUID
    case_id: uuid.UUID
    file_name: str | None
    file_type: str
    file_hash: str


class DummyIn(BaseModel):
    """A notice URL the user entered (not fetched) and/or a sample scenario key to use as the notice."""

    url: str | None = Field(default=None, min_length=3, max_length=2000)
    scenario: str | None = Field(default=None, max_length=40)


class AliasIn(BaseModel):
    text: str = Field(min_length=1)
    language: str = "en"


class KeywordIn(BaseModel):
    word: str = Field(min_length=1)
    weight: int = Field(default=10, ge=1, le=100)


class FineTierIn(BaseModel):
    label: str
    max_fine: int = Field(ge=0)
    keywords: list[str] = []


class OffenceRuleIn(BaseModel):
    section_number: str = Field(min_length=1)
    offence_title: str = Field(min_length=1)
    offence_description: str | None = None
    offence_category: str | None = None
    min_fine: int = Field(default=0, ge=0)
    max_fine: int | None = Field(default=None, ge=0)
    fine_text: str | None = None
    imprisonment_text: str | None = None
    repeat_rule_text: str | None = None
    source_reference: str | None = None
    matchable: bool = True
    fine_tiers: list[FineTierIn] = []
    aliases: list[AliasIn] = []
    keywords: list[KeywordIn] = []


class OffenceRuleCreate(OffenceRuleIn):
    dataset_version_id: uuid.UUID | None = Field(default=None, description="Defaults to the open draft version")


class ExceptionRuleIn(BaseModel):
    rule_key: str = Field(min_length=1)
    exception_title: str = Field(min_length=1)
    exception_description: str = ""
    applies_to_section: str | None = None
    applies_to_category: str | None = None
    effect: str = Field(default="exempts", pattern="^(exempts|permission_based|no_general_exemption|repealed)$")
    vehicle_types: list[str] = []
    conditions_text: list[str] = []
    scope_limit: str | None = None
    required_evidence: str | None = None
    source_reference: str | None = None
    keywords: list[KeywordIn] = []


class ExceptionRuleCreate(ExceptionRuleIn):
    dataset_version_id: uuid.UUID | None = None


class VersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class Anything(BaseModel):
    model_config = ConfigDict(extra="allow")


JsonDict = dict[str, Any]
__all__ = [n for n in dir() if not n.startswith("_")] + ["date"]
