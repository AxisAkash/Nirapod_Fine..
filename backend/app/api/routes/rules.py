from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.security import get_current_user
from app.db.session import get_db
from app.services.datasets import get_active_version

router = APIRouter(prefix="/offence-rules", tags=["offence rules"])


@router.get("")
def list_rules(
    q: str | None = Query(None, description="Search section, title or alias"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> dict:
    version = get_active_version(db)
    if version is None:
        raise HTTPException(503, "No active dataset version")
    rows = db.scalars(
        select(models.OffenceRule)
        .where(models.OffenceRule.dataset_version_id == version.id, models.OffenceRule.is_active.is_(True))
        .options(selectinload(models.OffenceRule.aliases))
    ).all()
    if q:
        needle = q.lower().strip()
        rows = [r for r in rows if needle in f"{r.section_number} {r.offence_title} {r.offence_category} "
                f"{' '.join(a.alias_text for a in r.aliases)}".lower()]
    rows.sort(key=lambda r: (int("".join(ch for ch in r.section_number.split("(")[0] if ch.isdigit()) or 0), r.section_number))
    return {
        "dataset": {"id": str(version.id), "name": version.version_name},
        "items": [
            {"id": str(r.id), "section_number": r.section_number, "offence_title": r.offence_title,
             "category": r.offence_category, "min_fine": r.min_fine, "max_fine": r.max_fine, "fine_text": r.fine_text,
             "imprisonment_text": r.imprisonment_text, "matchable": r.matchable, "fine_tiers": r.fine_tiers or []}
            for r in rows
        ],
    }
