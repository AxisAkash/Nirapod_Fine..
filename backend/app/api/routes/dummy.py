from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.api.serializers import case_detail
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import DummyIn
from app.services import analysis, dummy

router = APIRouter(prefix="/dummy-url", tags=["sample notices"])


@router.get("/scenarios")
def scenarios(user: models.User = Depends(get_current_user)) -> list[dict]:
    """The sample notices that can be used in place of a real external mamla source."""
    return dummy.list_scenarios()


@router.get("/preview")
def preview(
    url: str | None = Query(None, min_length=3),
    scenario: str | None = Query(None),
    user: models.User = Depends(get_current_user),
) -> dict:
    """The sample data a URL or scenario would return, without saving anything."""
    if not url and not scenario:
        raise HTTPException(422, "Give a url or a scenario.")
    return dummy.mock_mamla(url, scenario)


@router.post("/analyze", status_code=201)
def analyze_dummy(body: DummyIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)) -> dict:
    """Use a sample notice (nothing is fetched from the URL) and run it through the same analysis as a receipt."""
    if not body.url and not body.scenario:
        raise HTTPException(422, "Give a url or a scenario.")
    if body.scenario and dummy.scenario_by_key(body.scenario) is None:
        raise HTTPException(422, f"Unknown sample scenario '{body.scenario}'.")
    case = analysis.create_case(db, user, "dummy_url", dummy.mock_mamla(body.url, body.scenario), dummy_url=body.url)
    try:
        case = analysis.analyze_case(db, case)
    except analysis.AnalysisError as e:
        raise HTTPException(503, str(e)) from e
    return case_detail(case)
