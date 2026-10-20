import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.api.serializers import reading_out
from app.schemas import ReadingOut, UploadOut
from app.services import analysis, receipt_reader, storage

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/upload", response_model=UploadOut, status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    read: bool = Form(True),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> UploadOut:
    """Store the receipt file, hash it, and open a case. Every detail comes from reading the file; none can be typed in."""
    limit = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(limit + 1)
    try:
        stored = storage.save_upload(user.id, content)
    except storage.UploadError as e:
        raise HTTPException(e.status_code, str(e)) from e
    receipt = models.UploadedReceipt(
        user_id=user.id, file_url=stored.relative_path, file_name=file.filename, file_type=stored.file_type,
        file_hash=stored.sha256,
    )
    db.add(receipt)
    db.flush()
    case = analysis.create_case(db, user, "receipt_upload", {}, receipt)
    db.commit()
    message = None
    if read:
        # Read the file now so the user can check the fields before any legal comparison. Never raises.
        outcome = receipt_reader.read_receipt(db, receipt, content, stored.file_type, user)
        message = outcome.message
        db.commit()
    return UploadOut(receipt_id=receipt.id, case_id=case.id, file_name=receipt.file_name, file_type=stored.file_type,
                     file_hash=stored.sha256, reading=reading_out(receipt, message))


@router.post("/{receipt_id}/read", response_model=ReadingOut)
def read_again(receipt_id: uuid.UUID, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)) -> ReadingOut:
    """Read a stored receipt again, for example after a failed attempt."""
    receipt = db.scalar(select(models.UploadedReceipt).where(
        models.UploadedReceipt.id == receipt_id, models.UploadedReceipt.user_id == user.id))
    if receipt is None:
        raise HTTPException(404, "Receipt not found")
    try:
        path = storage.resolve_path(receipt.file_url)
        content = path.read_bytes()
    except (storage.UploadError, OSError) as e:
        raise HTTPException(404, "Receipt file not found") from e
    outcome = receipt_reader.read_receipt(db, receipt, content, receipt.file_type or "", user)
    db.commit()
    return reading_out(receipt, outcome.message)


@router.get("/{receipt_id}/file")
def download_receipt(receipt_id: uuid.UUID, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    receipt = db.scalar(select(models.UploadedReceipt).where(
        models.UploadedReceipt.id == receipt_id, models.UploadedReceipt.user_id == user.id))
    if receipt is None:
        raise HTTPException(404, "Receipt not found")
    try:
        path = storage.resolve_path(receipt.file_url)
    except storage.UploadError as e:
        raise HTTPException(404, "Receipt file not found") from e
    if not path.exists():
        raise HTTPException(404, "Receipt file not found")
    return FileResponse(path, media_type=receipt.file_type or "application/octet-stream", filename=receipt.file_name)
