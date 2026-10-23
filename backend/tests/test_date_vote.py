"""The date is chosen by vote when the readings of a receipt disagree."""

import json
from types import SimpleNamespace

from app.services.receipt_reader import _date_from_transcript, settle_date


def reading(date_value, transcript="Date 18/08/2026"):
    return {"transcript": transcript, "fields": {"date": {"value": date_value, "status": "read"}}}


class FakeClient:
    """Answers the focused date question with the given dates, one per call, and counts the calls."""

    def __init__(self, *dates):
        self.dates = list(dates)
        self.calls = 0

    def complete(self, *args, **kwargs):
        self.calls += 1
        y, m, d = (int(x) for x in self.dates.pop(0).split("-"))
        return SimpleNamespace(text=json.dumps({"date_text": "x", "day": d, "month": m, "year": y}))


def settle(passes, client):
    merged = passes[0]
    settle_date(passes, merged, client, [])
    return merged["fields"]["date"]


def test_the_date_in_the_transcript_is_found_in_latin_and_bangla_digits():
    assert _date_from_transcript("Date 18/08/2026") == "2026-08-18"
    assert _date_from_transcript("তারিখ ১৮/০৮/২০২৬") == "2026-08-18"
    assert _date_from_transcript("no date here") is None


def test_agreeing_readings_need_no_extra_read():
    client = FakeClient()
    field = settle([reading("2026-08-18"), reading("2026-08-18")], client)
    assert client.calls == 0 and field["value"] == "2026-08-18" and field["status"] == "read"


def test_a_misread_digit_is_outvoted():
    # the first reading's field says the 17th, but its transcript, the other reading and both extra reads say the 18th
    first = reading("2026-08-17")
    second = reading("2026-08-18")
    field = settle([first, second], FakeClient("2026-08-18", "2026-08-18"))
    assert field["value"] == "2026-08-18" and field["status"] == "read"


def test_a_date_nobody_agrees_on_stays_unverified():
    first = reading("2026-08-17", transcript="no date printed")
    second = reading("2026-08-19", transcript="no date printed")
    field = settle([first, second], FakeClient("2026-08-21", "2026-08-23"))
    assert field["status"] == "unverified" and "note" in field


def test_failed_extra_reads_leave_the_first_reading_flagged_not_lost():
    class Broken:
        def complete(self, *a, **k):
            from app.services.openrouter import AIError

            raise AIError("server", "down")

    first = reading("2026-08-17", transcript="no date printed")
    second = reading("2026-08-19", transcript="no date printed")
    field = settle([first, second], Broken())
    assert field["value"] in {"2026-08-17", "2026-08-19"} and field["status"] == "unverified"
