from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.deps import owned_case
from app.api.serializers import case_detail, case_list_item
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import CaseList
from app.services import analysis, sealing

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CaseList)
def list_cases(
    status: str | None = Query(None, description="Filter by validation status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> CaseList:
    q = select(models.MamlaCase).where(models.MamlaCase.user_id == user.id)
    if status:
        q = q.where(models.MamlaCase.validation_status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(models.MamlaCase.created_at.desc()).limit(limit).offset(offset)).all()
    return CaseList(items=[case_list_item(c) for c in rows], total=total)


@router.get("/{case_id}")
def get_case(case: models.MamlaCase = Depends(owned_case)) -> dict:
    return case_detail(case)


@router.post("/{case_id}/analyze")
def analyze(
    case: models.MamlaCase = Depends(owned_case),
    db: Session = Depends(get_db),
) -> dict:
    """Run the engine on the case as stored. Analysing again replaces the earlier result."""
    try:
        case = analysis.analyze_case(db, case)
    except analysis.AnalysisError as e:
        raise HTTPException(503, str(e)) from e
    return case_detail(case)


@router.get("/{case_id}/verify")
def verify(case: models.MamlaCase = Depends(owned_case), db: Session = Depends(get_db)) -> dict:
    """Recompute the case, dataset and result fingerprints from the database and compare them with the blockchain."""
    return sealing.verify_case(db, case)
