"""Dataset administration. Admin role only. Only draft versions can be edited; the active one is read-only."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.security import require_admin
from app.db.session import get_db
from app.schemas import ExceptionRuleCreate, ExceptionRuleIn, OffenceRuleCreate, OffenceRuleIn, VersionCreate
from app.services import datasets

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- helpers -------------------------------------------------------------------------------------
def _version(db: Session, version_id: uuid.UUID) -> models.DatasetVersion:
    v = db.get(models.DatasetVersion, version_id)
    if v is None:
        raise HTTPException(404, "Dataset version not found")
    return v


def _editable(db: Session, version_id: uuid.UUID | None) -> models.DatasetVersion:
    """The version being edited: the one given, or the single open draft."""
    if version_id is None:
        drafts = db.scalars(select(models.DatasetVersion).where(models.DatasetVersion.status == "draft")).all()
        if len(drafts) != 1:
            raise HTTPException(409, "Specify dataset_version_id: there must be exactly one draft to default to.")
        v = drafts[0]
    else:
        v = _version(db, version_id)
    try:
        datasets.require_draft(v)
    except datasets.DatasetError as e:
        raise HTTPException(409, str(e)) from e
    return v


def _version_out(db: Session, v: models.DatasetVersion) -> dict[str, Any]:
    rules = db.scalar(select(func.count()).select_from(models.OffenceRule).where(models.OffenceRule.dataset_version_id == v.id))
    exc = db.scalar(select(func.count()).select_from(models.ExceptionRule).where(models.ExceptionRule.dataset_version_id == v.id))
    return {"id": str(v.id), "version_name": v.version_name, "description": v.description, "status": v.status,
            "is_active": v.is_active, "source_file_name": v.source_file_name, "source_hash": v.source_hash,
            "created_at": v.created_at.isoformat(), "offence_rule_count": rules, "exception_rule_count": exc}


def _rule_out(r: models.OffenceRule) -> dict[str, Any]:
    return {"id": str(r.id), "dataset_version_id": str(r.dataset_version_id), "section_number": r.section_number,
            "offence_title": r.offence_title, "offence_description": r.offence_description,
            "offence_category": r.offence_category, "min_fine": r.min_fine, "max_fine": r.max_fine,
            "fine_text": r.fine_text, "imprisonment_text": r.imprisonment_text, "repeat_rule_text": r.repeat_rule_text,
            "source_reference": r.source_reference, "matchable": r.matchable, "fine_tiers": r.fine_tiers or [],
            "aliases": [{"text": a.alias_text, "language": a.language} for a in r.aliases],
            "keywords": [{"word": k.keyword, "weight": k.weight} for k in r.keywords]}


def _exc_out(x: models.ExceptionRule) -> dict[str, Any]:
    c = x.conditions or {}
    return {"id": str(x.id), "dataset_version_id": str(x.dataset_version_id), "rule_key": x.rule_key,
            "exception_title": x.exception_title, "exception_description": x.exception_description,
            "applies_to_section": x.applies_to_section, "applies_to_category": x.applies_to_category,
            "effect": c.get("effect"), "vehicle_types": c.get("vehicle_types", []),
            "conditions_text": c.get("conditions_text", []), "scope_limit": x.scope_limit,
            "required_evidence": x.required_evidence, "source_reference": x.source_reference,
            "keywords": [{"word": k.keyword, "weight": k.weight} for k in x.keywords]}


def _apply_rule(row: models.OffenceRule, body: OffenceRuleIn) -> None:
    row.section_number = body.section_number
    row.offence_title = body.offence_title
    row.offence_description = body.offence_description or body.offence_title
    row.offence_category = body.offence_category
    row.min_fine, row.max_fine = body.min_fine, body.max_fine
    row.fine_text, row.imprisonment_text = body.fine_text, body.imprisonment_text
    row.repeat_rule_text, row.source_reference = body.repeat_rule_text, body.source_reference
    row.matchable = body.matchable
    row.fine_tiers = [t.model_dump() for t in body.fine_tiers] or None
    row.aliases = [models.OffenceAlias(alias_text=a.text, language=a.language) for a in body.aliases]
    row.keywords = [models.OffenceKeyword(keyword=k.word, weight=k.weight) for k in body.keywords]


def _apply_exception(row: models.ExceptionRule, body: ExceptionRuleIn) -> None:
    row.rule_key = body.rule_key
    row.exception_title = body.exception_title
    row.exception_description = body.exception_description
    row.applies_to_section, row.applies_to_category = body.applies_to_section, body.applies_to_category
    row.scope_limit, row.required_evidence = body.scope_limit, body.required_evidence
    row.source_reference = body.source_reference
    row.conditions = {"effect": body.effect, "vehicle_types": body.vehicle_types, "conditions_text": body.conditions_text}
    row.keywords = [models.ExceptionKeyword(keyword=k.word, weight=k.weight) for k in body.keywords]


def _commit(db: Session, what: str) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, f"{what} already exists in this dataset version.") from e


# ---------- dataset versions -------------------------------------------------------------------------
@router.get("/dataset-versions")
def list_versions(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(models.DatasetVersion).order_by(models.DatasetVersion.created_at.desc())).all()
    return [_version_out(db, v) for v in rows]


@router.post("/dataset-versions", status_code=201)
def create_draft(body: VersionCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Clone the active version into a new draft. Only one draft can be open at a time."""
    if db.scalar(select(models.DatasetVersion).where(models.DatasetVersion.status == "draft")):
        raise HTTPException(409, "A draft already exists. Activate or finish it first.")
    active = datasets.get_active_version(db)
    if active is None:
        raise HTTPException(409, "There is no active version to clone.")
    try:
        draft = datasets.clone_version(db, active, body.name, body.description)
    except datasets.DatasetError as e:
        raise HTTPException(409, str(e)) from e
    db.commit()
    return _version_out(db, draft)


@router.post("/dataset-versions/{version_id}/activate")
def activate(version_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    v = _version(db, version_id)
    try:
        datasets.activate_version(db, v)
    except datasets.DatasetError as e:
        raise HTTPException(409, str(e)) from e
    db.commit()
    return _version_out(db, v)


@router.get("/dataset-versions/{version_id}/hash")
def version_hash(version_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    v = _version(db, version_id)
    return {"version_id": str(v.id), "source_hash": v.source_hash, "content_hash": datasets.dataset_content_hash(db, v)}


# ---------- offence rules ----------------------------------------------------------------------------------
@router.get("/offence-rules")
def list_rules(version_id: uuid.UUID | None = Query(None), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    v = _version(db, version_id) if version_id else datasets.get_active_version(db)
    if v is None:
        return []
    rows = db.scalars(select(models.OffenceRule).where(models.OffenceRule.dataset_version_id == v.id)
                      .options(selectinload(models.OffenceRule.aliases), selectinload(models.OffenceRule.keywords))
                      .order_by(models.OffenceRule.section_number)).all()
    return [_rule_out(r) for r in rows]


@router.post("/offence-rules", status_code=201)
def create_rule(body: OffenceRuleCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    v = _editable(db, body.dataset_version_id)
    row = models.OffenceRule(dataset_version_id=v.id)
    _apply_rule(row, body)
    db.add(row)
    _commit(db, f"Section {body.section_number}")
    return _rule_out(row)


def _draft_rule(db: Session, rule_id: uuid.UUID) -> models.OffenceRule:
    row = db.get(models.OffenceRule, rule_id)
    if row is None:
        raise HTTPException(404, "Rule not found")
    _editable(db, row.dataset_version_id)
    return row


@router.put("/offence-rules/{rule_id}")
def update_rule(rule_id: uuid.UUID, body: OffenceRuleIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _draft_rule(db, rule_id)
    _apply_rule(row, body)
    _commit(db, f"Section {body.section_number}")
    return _rule_out(row)


@router.delete("/offence-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = _draft_rule(db, rule_id)
    db.delete(row)
    db.commit()


# ---------- exception rules ------------------------------------------------------------------------------
@router.get("/exception-rules")
def list_exceptions(version_id: uuid.UUID | None = Query(None), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    v = _version(db, version_id) if version_id else datasets.get_active_version(db)
    if v is None:
        return []
    rows = db.scalars(select(models.ExceptionRule).where(models.ExceptionRule.dataset_version_id == v.id)
                      .options(selectinload(models.ExceptionRule.keywords)).order_by(models.ExceptionRule.rule_key)).all()
    return [_exc_out(x) for x in rows]


@router.post("/exception-rules", status_code=201)
def create_exception(body: ExceptionRuleCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    v = _editable(db, body.dataset_version_id)
    row = models.ExceptionRule(dataset_version_id=v.id)
    _apply_exception(row, body)
    db.add(row)
    _commit(db, f"Exception '{body.rule_key}'")
    return _exc_out(row)


def _draft_exception(db: Session, rule_id: uuid.UUID) -> models.ExceptionRule:
    row = db.get(models.ExceptionRule, rule_id)
    if row is None:
        raise HTTPException(404, "Exception rule not found")
    _editable(db, row.dataset_version_id)
    return row


@router.put("/exception-rules/{rule_id}")
def update_exception(rule_id: uuid.UUID, body: ExceptionRuleIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _draft_exception(db, rule_id)
    _apply_exception(row, body)
    _commit(db, f"Exception '{body.rule_key}'")
    return _exc_out(row)


@router.delete("/exception-rules/{rule_id}", status_code=204)
def delete_exception(rule_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = _draft_exception(db, rule_id)
    db.delete(row)
    db.commit()
