"""Stand-in for an external AI mamla service. The words in the URL choose a repeatable scenario."""

from __future__ import annotations

from typing import Any

SCENARIOS: list[dict[str, Any]] = [
    {"match": "speed", "reason": "exceeding speed limit", "amount": 3000, "vehicle": "motorcycle", "section": "87",
     "location": "Dhaka", "date": "2026-10-12", "notes": ""},
    {"match": "permit", "reason": "no route permit", "amount": 5000, "vehicle": "ambulance", "section": "77",
     "location": "Dhaka", "date": "2026-10-10", "notes": ""},
    {"match": "park", "reason": "parking violation", "amount": 9000, "vehicle": "car", "section": "90",
     "location": "Sylhet", "date": "2026-10-11", "notes": ""},
    {"match": "signal", "reason": "red light violation", "amount": 3000, "vehicle": "car", "section": "88",
     "location": "Khulna", "date": "2026-10-09", "notes": ""},
    {"match": "tax", "reason": "tax token expired", "amount": 4000, "vehicle": "truck", "section": "",
     "location": "Rajshahi", "date": "2026-10-08", "notes": ""},
    {"match": "emergency", "reason": "speeding", "amount": 4000, "vehicle": "ambulance", "section": "",
     "location": "Dhaka", "date": "2026-10-07", "notes": "rushing patient to hospital"},
]


def mock_mamla(url: str) -> dict[str, Any]:
    low = url.lower()
    pick = next((s for s in SCENARIOS if s["match"] in low), None) or SCENARIOS[sum(map(ord, url)) % len(SCENARIOS)]
    number = f"AIM-{sum(map(ord, url)) % 9000 + 1000}"
    return {**{k: v for k, v in pick.items() if k != "match"}, "receipt_number": number}
