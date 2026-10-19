from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.api.deps import owned_case
from app.api.serializers import audit_summary
from app.core.security import get_current_user
from app.db.session import get_db
from app.services import sealing

router = APIRouter(prefix="/blockchain", tags=["blockchain audit"])


class RecordIn(BaseModel):
    case_id: str


@router.post("/record")
def record(body: RecordIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)) -> dict:
    """Record a case on the blockchain, or retry a record that is pending or failed. A sealed record is left as it is."""
    case = owned_case(body.case_id, db, user)  # type: ignore[arg-type]
    if case.records:
        sealing.retry_record(db, case)
    else:
        sealing.seal_case(db, case)
    db.commit()
    db.refresh(case)
    return audit_summary(case)
