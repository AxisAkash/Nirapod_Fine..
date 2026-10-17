from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api.serializers import case_detail
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import DummyIn
from app.services import analysis, dummy

router = APIRouter(prefix="/dummy-url", tags=["dummy mamla URL"])


@router.get("/preview")
def preview(url: str = Query(..., min_length=3), user: models.User = Depends(get_current_user)) -> dict:
    """The mamla data a URL would return, without saving anything."""
    return dummy.mock_mamla(url)


@router.post("/analyze", status_code=201)
def analyze_dummy(body: DummyIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)) -> dict:
    """Fetch mock mamla data for the URL, then run it through the same analysis as an uploaded receipt."""
    case = analysis.create_case(db, user, "dummy_url", dummy.mock_mamla(body.url), dummy_url=body.url)
    try:
        case = analysis.analyze_case(db, case)
    except analysis.AnalysisError as e:
        raise HTTPException(503, str(e)) from e
    return case_detail(case)
