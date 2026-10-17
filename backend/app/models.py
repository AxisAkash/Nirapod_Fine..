"""SQLAlchemy models. Table and column names follow the project schema; additions are marked 'added'."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# JSONB on PostgreSQL; plain JSON elsewhere so the models can still be inspected without a server.
JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    """Naive UTC, matching the TIMESTAMP (without time zone) columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime, default=utcnow, server_default=text("now()"))


def _updated() -> Mapped[datetime]:
    return mapped_column(DateTime, default=utcnow, onupdate=utcnow, server_default=text("now()"))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _id()
    clerk_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="user", server_default="user")
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = _id()
    version_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_file_name: Mapped[str | None] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    # added: draft | active | archived. Only draft versions can be edited; is_active mirrors status == 'active'.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft", server_default="draft")
    created_at: Mapped[datetime] = _created()

    rules: Mapped[list[OffenceRule]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    exceptions: Mapped[list[ExceptionRule]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")

    __table_args__ = (
        # at most one active version at any time
        Index("uq_one_active_dataset", "is_active", unique=True, postgresql_where=text("is_active")),
    )


class OffenceRule(Base):
    __tablename__ = "offence_rules"

    id: Mapped[uuid.UUID] = _id()
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    section_number: Mapped[str] = mapped_column(Text, nullable=False)
    offence_title: Mapped[str] = mapped_column(Text, nullable=False)
    offence_description: Mapped[str] = mapped_column(Text, nullable=False)
    offence_category: Mapped[str | None] = mapped_column(Text)
    min_fine: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_fine: Mapped[int | None] = mapped_column(Integer)
    fine_text: Mapped[str | None] = mapped_column(Text)
    imprisonment_text: Mapped[str | None] = mapped_column(Text)
    penalty_points: Mapped[int | None] = mapped_column(Integer)
    repeat_rule_text: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # added: supporting provisions (99, 100) are stored but never auto-matched
    matchable: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # added: [{"label": ..., "max_fine": ..., "keywords": [...]}] for sections with more than one ceiling (s.82)
    fine_tiers: Mapped[list[dict[str, Any]] | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="rules")
    aliases: Mapped[list[OffenceAlias]] = relationship(back_populates="rule", cascade="all, delete-orphan")
    keywords: Mapped[list[OffenceKeyword]] = relationship(back_populates="rule", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("dataset_version_id", "section_number", name="uq_rule_version_section"),)


class OffenceAlias(Base):
    __tablename__ = "offence_aliases"

    id: Mapped[uuid.UUID] = _id()
    offence_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offence_rules.id", ondelete="CASCADE"), nullable=False
    )
    alias_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, default="en", server_default="en")
    created_at: Mapped[datetime] = _created()

    rule: Mapped[OffenceRule] = relationship(back_populates="aliases")


class OffenceKeyword(Base):
    __tablename__ = "offence_keywords"

    id: Mapped[uuid.UUID] = _id()
    offence_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offence_rules.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    created_at: Mapped[datetime] = _created()

    rule: Mapped[OffenceRule] = relationship(back_populates="keywords")


class ExceptionRule(Base):
    __tablename__ = "exception_rules"

    id: Mapped[uuid.UUID] = _id()
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    # added: stable identifier that survives cloning a dataset version
    rule_key: Mapped[str] = mapped_column(Text, nullable=False)
    exception_title: Mapped[str] = mapped_column(Text, nullable=False)
    exception_description: Mapped[str] = mapped_column(Text, nullable=False)
    applies_to_section: Mapped[str | None] = mapped_column(Text)
    applies_to_category: Mapped[str | None] = mapped_column(Text)
    # {"effect": ..., "vehicle_types": [...], "conditions_text": [...]}
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    scope_limit: Mapped[str | None] = mapped_column(Text)
    required_evidence: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="exceptions")
    keywords: Mapped[list[ExceptionKeyword]] = relationship(back_populates="rule", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("dataset_version_id", "rule_key", name="uq_exception_version_key"),)


class ExceptionKeyword(Base):
    __tablename__ = "exception_keywords"

    id: Mapped[uuid.UUID] = _id()
    exception_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exception_rules.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    created_at: Mapped[datetime] = _created()

    rule: Mapped[ExceptionRule] = relationship(back_populates="keywords")


class UploadedReceipt(Base):
    __tablename__ = "uploaded_receipts"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    file_url: Mapped[str] = mapped_column(Text, nullable=False)  # path relative to the storage directory
    file_name: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str | None] = mapped_column(Text)
    file_hash: Mapped[str | None] = mapped_column(Text)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()


class MamlaCase(Base):
    __tablename__ = "mamla_cases"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_receipts.id", ondelete="SET NULL")
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dataset_versions.id"))
    case_source: Mapped[str] = mapped_column(Text, nullable=False, default="receipt_upload", server_default="receipt_upload")
    dummy_url: Mapped[str | None] = mapped_column(Text)
    extracted_reason: Mapped[str | None] = mapped_column(Text)
    extracted_amount: Mapped[int | None] = mapped_column(Integer)
    extracted_date: Mapped[date | None] = mapped_column(Date)
    extracted_location: Mapped[str | None] = mapped_column(Text)
    extracted_vehicle_type: Mapped[str | None] = mapped_column(Text)
    extracted_receipt_number: Mapped[str | None] = mapped_column(Text)
    # added: section cited on the receipt, the driver's claimed exception / notes, and raw user input
    extracted_section: Mapped[str | None] = mapped_column(Text)
    claim_notes: Mapped[str | None] = mapped_column(Text)
    manual_input: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    # added: the complete engine output, so pages render without recomputing
    analysis_details: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    matched_offence_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offence_rules.id", ondelete="SET NULL")
    )
    validation_status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING_ANALYSIS")
    validation_summary: Mapped[str | None] = mapped_column(Text)
    ai_explanation: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    blockchain_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    receipt: Mapped[UploadedReceipt | None] = relationship()
    dataset_version: Mapped[DatasetVersion | None] = relationship()
    matched_rule: Mapped[OffenceRule | None] = relationship(foreign_keys=[matched_offence_rule_id])
    matches: Mapped[list[MamlaCaseMatch]] = relationship(cascade="all, delete-orphan", order_by="MamlaCaseMatch.match_score.desc()")
    exception_checks: Mapped[list[MamlaExceptionCheck]] = relationship(cascade="all, delete-orphan")

    __table_args__ = (Index("ix_mamla_cases_user_created", "user_id", "created_at"),)


class MamlaCaseMatch(Base):
    __tablename__ = "mamla_case_matches"

    id: Mapped[uuid.UUID] = _id()
    mamla_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mamla_cases.id", ondelete="CASCADE"))
    offence_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offence_rules.id"))
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()

    rule: Mapped[OffenceRule] = relationship()


class MamlaExceptionCheck(Base):
    __tablename__ = "mamla_exception_checks"

    id: Mapped[uuid.UUID] = _id()
    mamla_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mamla_cases.id", ondelete="CASCADE"))
    exception_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exception_rules.id"))
    applies: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()

    rule: Mapped[ExceptionRule] = relationship()


class MamlaHistory(Base):
    __tablename__ = "mamla_history"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    offence_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offence_rules.id"))
    mamla_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mamla_cases.id", ondelete="CASCADE"))
    fine_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # added: the section as text and the case time, so repeat checks need no join through dataset versions
    section_number: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = _created()

    __table_args__ = (Index("ix_history_user_section", "user_id", "section_number", "occurred_at"),)


class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"

    id: Mapped[uuid.UUID] = _id()
    mamla_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mamla_cases.id", ondelete="CASCADE"))
    case_hash: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_hash: Mapped[str] = mapped_column(Text, nullable=False)
    result_hash: Mapped[str] = mapped_column(Text, nullable=False)
    blockchain_network: Mapped[str | None] = mapped_column(Text)
    smart_contract_address: Mapped[str | None] = mapped_column(Text)
    transaction_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
