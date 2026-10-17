"""Stand-in for an external AI mamla service. A scenario key or words in the URL choose a repeatable sample."""

from __future__ import annotations

from typing import Any

SCENARIOS: list[dict[str, Any]] = [
    {"key": "speed", "reason": "exceeding speed limit", "amount": 3000, "vehicle": "motorcycle", "section": "87",
     "location": "Dhaka", "date": "2026-10-12", "notes": ""},
    {"key": "permit", "reason": "no route permit", "amount": 5000, "vehicle": "ambulance", "section": "77",
     "location": "Dhaka", "date": "2026-10-10", "notes": ""},
    {"key": "park", "reason": "parking violation", "amount": 9000, "vehicle": "car", "section": "90",
     "location": "Sylhet", "date": "2026-10-11", "notes": ""},
    {"key": "signal", "reason": "red light violation", "amount": 3000, "vehicle": "car", "section": "88",
     "location": "Khulna", "date": "2026-10-09", "notes": ""},
    {"key": "tax", "reason": "tax token expired", "amount": 4000, "vehicle": "truck", "section": "",
     "location": "Rajshahi", "date": "2026-10-08", "notes": ""},
    {"key": "emergency", "reason": "speeding", "amount": 4000, "vehicle": "ambulance", "section": "",
     "location": "Dhaka", "date": "2026-10-07", "notes": "rushing patient to hospital"},
]


def _number(seed: str) -> str:
    return f"AIM-{sum(map(ord, seed)) % 9000 + 1000}"


def scenario_by_key(key: str) -> dict[str, Any] | None:
    return next((s for s in SCENARIOS if s["key"] == key), None)


def mock_mamla(url: str | None = None, scenario: str | None = None) -> dict[str, Any]:
    """Sample notice data. An explicit scenario wins, then a scenario word in the URL, then a stable pick."""
    pick = scenario_by_key(scenario) if scenario else None
    low = (url or "").lower()
    if pick is None:
        pick = next((s for s in SCENARIOS if s["key"] in low), None)
    if pick is None:
        pick = SCENARIOS[sum(map(ord, url or "")) % len(SCENARIOS)]
    return {**{k: v for k, v in pick.items() if k != "key"}, "receipt_number": _number(pick["key"] if scenario else (url or pick["key"]))}


def list_scenarios() -> list[dict[str, Any]]:
    return [{"key": s["key"], **mock_mamla(scenario=s["key"])} for s in SCENARIOS]
