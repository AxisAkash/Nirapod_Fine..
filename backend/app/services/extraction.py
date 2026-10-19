"""Fields read from a receipt file. They are only defaults: anything the user typed or corrected overrides them."""

from __future__ import annotations

from typing import Any

from app import models
from app.services.receipt_reader import fields_for_case


def extract_fields(receipt: models.UploadedReceipt | None) -> dict[str, Any]:
    return fields_for_case(receipt)
