"""Dataset versions: load into the engine, seed from the PDFs, clone to a draft, activate."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.config import BACKEND_DIR
from app.core.hashing import hash_object, sha256_bytes, sha256_text
from app.engine.models import Dataset, ExceptionRule, FineTier, Keyword, OffenceRule
from app.seed import data as seed

SOURCE_DIR = BACKEND_DIR.parent / "data" / "source"


class DatasetError(Exception):
    """Raised for rule violations such as editing an active version."""


@dataclass
class LoadedDataset:
    version: models.DatasetVersion
    dataset: Dataset
    rule_ids: dict[str, uuid.UUID]  # section number -> offence_rules.id
    exception_ids: dict[str, uuid.UUID]  # rule_key -> exception_rules.id


def get_active_version(db: Session) -> models.DatasetVersion | None:
    return db.scalar(select(models.DatasetVersion).where(models.DatasetVersion.is_active.is_(True)))


def load_engine_dataset(db: Session, version: models.DatasetVersion) -> LoadedDataset:
    rows = db.scalars(
        select(models.OffenceRule)
        .where(models.OffenceRule.dataset_version_id == version.id, models.OffenceRule.is_active.is_(True))
        .options(selectinload(models.OffenceRule.aliases), selectinload(models.OffenceRule.keywords))
        .order_by(models.OffenceRule.created_at, models.OffenceRule.section_number)
    ).all()
    rules, rule_ids = [], {}
    for r in rows:
        rules.append(
            OffenceRule(
                section=r.section_number,
                title=r.offence_title,
                category=r.offence_category or "",
                min_fine=r.min_fine or 0,
                max_fine=r.max_fine,
                fine_text=r.fine_text or "",
                imprisonment_text=r.imprisonment_text,
                repeat_rule_text=r.repeat_rule_text,
                source_reference=r.source_reference or "",
                aliases=[a.alias_text for a in r.aliases],
                keywords=[Keyword(k.keyword, k.weight) for k in r.keywords],
                matchable=r.matchable,
                fine_tiers=[
                    FineTier(t["label"], t["max_fine"], tuple(t.get("keywords", []))) for t in (r.fine_tiers or [])
                ],
            )
        )
        rule_ids[r.section_number] = r.id

    xrows = db.scalars(
        select(models.ExceptionRule)
        .where(models.ExceptionRule.dataset_version_id == version.id, models.ExceptionRule.is_active.is_(True))
        .options(selectinload(models.ExceptionRule.keywords))
        .order_by(models.ExceptionRule.created_at, models.ExceptionRule.rule_key)
    ).all()
    exceptions, exception_ids = [], {}
    for x in xrows:
        cond = x.conditions or {}
        exceptions.append(
            ExceptionRule(
                key=x.rule_key,
                title=x.exception_title,
                category=x.applies_to_category or "*",
                effect=cond.get("effect", "exempts"),
                section=x.applies_to_section,
                description=x.exception_description,
                vehicles=list(cond.get("vehicle_types", [])),
                conditions_text=list(cond.get("conditions_text", [])),
                scope_limit=x.scope_limit or "",
                required_evidence=x.required_evidence or "",
                source_reference=x.source_reference or "",
                keywords=[Keyword(k.keyword, k.weight) for k in x.keywords],
            )
        )
        exception_ids[x.rule_key] = x.id
    return LoadedDataset(version, Dataset(version.version_name, rules, exceptions), rule_ids, exception_ids)


def dataset_content_hash(db: Session, version: models.DatasetVersion) -> str:
    """Hash of everything that can change a verdict. Recomputed on demand so later edits are detectable."""
    loaded = load_engine_dataset(db, version)
    payload = {
        "rules": [
            {
                "section": r.section, "title": r.title, "category": r.category, "min": r.min_fine, "max": r.max_fine,
                "matchable": r.matchable, "aliases": sorted(r.aliases),
                "keywords": sorted([k.word, k.weight] for k in r.keywords),
                "tiers": [[t.label, t.max_fine, sorted(t.keywords)] for t in r.fine_tiers],
            }
            for r in sorted(loaded.dataset.rules, key=lambda r: r.section)
        ],
        "exceptions": [
            {
                "key": x.key, "category": x.category, "section": x.section, "effect": x.effect,
                "vehicles": sorted(x.vehicles), "scope": x.scope_limit,
                "keywords": sorted([k.word, k.weight] for k in x.keywords),
            }
            for x in sorted(loaded.dataset.exceptions, key=lambda x: x.key)
        ],
    }
    return hash_object(payload)


def _source_hash() -> str:
    parts = []
    for name in seed.SOURCE_FILES:
        path = Path(SOURCE_DIR) / name
        parts.append(sha256_bytes(path.read_bytes()) if path.exists() else sha256_text(name))
    return sha256_text("".join(parts))


def _add_rule_rows(db: Session, version: models.DatasetVersion, rules: list[dict], exceptions: list[dict]) -> None:
    for r in rules:
        row = models.OffenceRule(
            dataset_version_id=version.id, section_number=r["section"], offence_title=r["title"],
            offence_description=r["description"], offence_category=r["category"], min_fine=r["min_fine"],
            max_fine=r["max_fine"], fine_text=r["fine_text"], imprisonment_text=r["imprisonment_text"],
            repeat_rule_text=r["repeat_rule_text"], source_reference=r["source_reference"],
            matchable=r["matchable"], fine_tiers=r.get("fine_tiers") or None,
        )
        row.aliases = [models.OffenceAlias(alias_text=a["text"], language=a["language"]) for a in r["aliases"]]
        row.keywords = [models.OffenceKeyword(keyword=k["word"], weight=k["weight"]) for k in r["keywords"]]
        db.add(row)
    for x in exceptions:
        row = models.ExceptionRule(
            dataset_version_id=version.id, rule_key=x["key"], exception_title=x["title"],
            exception_description=x["description"], applies_to_section=x["section"],
            applies_to_category=x["category"], scope_limit=x["scope_limit"],
            required_evidence=x["required_evidence"], source_reference=x["source_reference"],
            conditions={"effect": x["effect"], "vehicle_types": x["vehicles"], "conditions_text": x["conditions_text"]},
        )
        row.keywords = [models.ExceptionKeyword(keyword=k["word"], weight=k["weight"]) for k in x["keywords"]]
        db.add(row)


def seed_default_dataset(db: Session) -> models.DatasetVersion:
    """Load the PDF-derived dataset. Safe to run twice: an existing version with the same name is kept."""
    existing = db.scalar(select(models.DatasetVersion).where(models.DatasetVersion.version_name == seed.DATASET_NAME))
    if existing:
        return existing
    version = models.DatasetVersion(
        version_name=seed.DATASET_NAME, description=seed.DATASET_DESCRIPTION,
        source_file_name=", ".join(seed.SOURCE_FILES), source_hash=_source_hash(), status="draft", is_active=False,
    )
    db.add(version)
    db.flush()
    _add_rule_rows(db, version, seed.OFFENCE_RULES, seed.EXCEPTION_RULES)
    db.flush()
    if get_active_version(db) is None:
        activate_version(db, version)
    db.commit()
    return version


def activate_version(db: Session, version: models.DatasetVersion) -> None:
    if version.status == "archived":
        raise DatasetError("An archived version cannot be activated again. Create a new draft from the active one.")
    db.execute(
        update(models.DatasetVersion)
        .where(models.DatasetVersion.is_active.is_(True))
        .values(is_active=False, status="archived")
    )
    db.flush()
    version.is_active = True
    version.status = "active"
    db.flush()


def clone_version(db: Session, source: models.DatasetVersion, name: str, description: str | None = None) -> models.DatasetVersion:
    """Copy a version into a new editable draft."""
    if db.scalar(select(models.DatasetVersion).where(models.DatasetVersion.version_name == name)):
        raise DatasetError(f"A dataset version named '{name}' already exists.")
    draft = models.DatasetVersion(
        version_name=name, description=description or f"Draft cloned from {source.version_name}",
        source_file_name=source.source_file_name, source_hash=source.source_hash, status="draft", is_active=False,
    )
    db.add(draft)
    db.flush()
    for r in db.scalars(
        select(models.OffenceRule).where(models.OffenceRule.dataset_version_id == source.id)
        .options(selectinload(models.OffenceRule.aliases), selectinload(models.OffenceRule.keywords))
    ):
        copy = models.OffenceRule(
            dataset_version_id=draft.id, section_number=r.section_number, offence_title=r.offence_title,
            offence_description=r.offence_description, offence_category=r.offence_category, min_fine=r.min_fine,
            max_fine=r.max_fine, fine_text=r.fine_text, imprisonment_text=r.imprisonment_text,
            penalty_points=r.penalty_points, repeat_rule_text=r.repeat_rule_text, source_reference=r.source_reference,
            is_active=r.is_active, matchable=r.matchable, fine_tiers=r.fine_tiers,
        )
        copy.aliases = [models.OffenceAlias(alias_text=a.alias_text, language=a.language) for a in r.aliases]
        copy.keywords = [models.OffenceKeyword(keyword=k.keyword, weight=k.weight) for k in r.keywords]
        db.add(copy)
    for x in db.scalars(
        select(models.ExceptionRule).where(models.ExceptionRule.dataset_version_id == source.id)
        .options(selectinload(models.ExceptionRule.keywords))
    ):
        copy_x = models.ExceptionRule(
            dataset_version_id=draft.id, rule_key=x.rule_key, exception_title=x.exception_title,
            exception_description=x.exception_description, applies_to_section=x.applies_to_section,
            applies_to_category=x.applies_to_category, conditions=x.conditions, scope_limit=x.scope_limit,
            required_evidence=x.required_evidence, source_reference=x.source_reference, is_active=x.is_active,
        )
        copy_x.keywords = [models.ExceptionKeyword(keyword=k.keyword, weight=k.weight) for k in x.keywords]
        db.add(copy_x)
    db.flush()
    return draft


def require_draft(version: models.DatasetVersion) -> None:
    if version.status != "draft":
        raise DatasetError("Only a draft dataset version can be edited. Create a draft from the active version first.")
