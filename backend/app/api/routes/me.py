from fastapi import APIRouter, Depends

from app import models
from app.core.security import get_current_user
from app.schemas import UserOut

router = APIRouter(tags=["account"])


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)) -> models.User:
    return user
