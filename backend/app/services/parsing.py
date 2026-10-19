"""Parsing of receipt values typed by a user or read by the AI."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def parse_amount(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value).translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")))
    return int(digits) if digits else None


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None
