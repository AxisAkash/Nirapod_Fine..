import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.core.security import get_current_user
from app.db.session import get_db


def owned_case(case_id: uuid.UUID, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)) -> models.MamlaCase:
    """A case the signed-in user owns. Someone else's case looks exactly like a missing one."""
    case = db.scalar(select(models.MamlaCase).where(models.MamlaCase.id == case_id, models.MamlaCase.user_id == user.id))
    if case is None:
        raise HTTPException(404, "Case not found")
    return case
