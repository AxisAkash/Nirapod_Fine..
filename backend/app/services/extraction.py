"""Receipt field extraction. Phase 4 plugs OCR and the OpenRouter model in here; until then only user input is used."""

from __future__ import annotations

from typing import Any

from app import models


def extract_fields(receipt: models.UploadedReceipt | None) -> dict[str, Any]:
    """Return fields read from the receipt file. Empty for now; manual fields always take precedence."""
    return {}
