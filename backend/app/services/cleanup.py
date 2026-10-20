"""Removes receipts that were uploaded but never analysed.

A case is created the moment a file is uploaded, but it only becomes a check when the user analyses it. If they
walk away, the file and the empty case are deleted after `unanalysed_upload_max_age_hours`. Analysed cases are
never touched.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import analysis, storage

log = logging.getLogger(__name__)


def purge_unanalysed_uploads(db: Session, max_age: timedelta | None = None) -> int:
    """Delete stale unanalysed upload cases, their receipts and the stored files. Returns how many cases went."""
    max_age = max_age or timedelta(hours=get_settings().unanalysed_upload_max_age_hours)
    cutoff = models.utcnow() - max_age
    cases = db.scalars(
        select(models.MamlaCase).where(
            models.MamlaCase.case_source == "receipt_upload",
            models.MamlaCase.validation_status == analysis.PENDING,
            models.MamlaCase.created_at < cutoff,
            ~models.MamlaCase.records.any(),  # never remove anything that was written to the blockchain
        )
    ).all()
    files: list[str] = []
    for case in cases:
        receipt = case.receipt
        db.delete(case)
        if receipt is not None:
            files.append(receipt.file_url)
            db.flush()  # the case goes first: it points at the receipt
            db.delete(receipt)
    db.commit()
    for relative in files:  # only after the database change has been saved
        try:
            storage.resolve_path(relative).unlink(missing_ok=True)
        except (storage.UploadError, OSError):
            log.warning("Could not remove stored receipt file %s", relative)
    return len(cases)


def _purge_once() -> None:
    try:
        with SessionLocal() as db:
            removed = purge_unanalysed_uploads(db)
        if removed:
            log.info("Removed %d unanalysed upload(s)", removed)
    except Exception:  # a failed clean-up must never stop the API
        log.exception("Clean-up of unanalysed uploads failed")


async def run_cleanup_loop() -> None:
    """Runs once at start-up, then every hour, for as long as the API is running."""
    while True:
        await asyncio.to_thread(_purge_once)
        await asyncio.sleep(3600)
