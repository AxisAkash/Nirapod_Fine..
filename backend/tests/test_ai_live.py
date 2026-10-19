"""Calls the REAL AI service, so it is skipped unless you ask for it:   RUN_LIVE_AI=1 pytest tests/test_ai_live.py

Uses OPENROUTER_API_KEY from backend/.env and costs a fraction of a cent per run.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_AI") != "1", reason="set RUN_LIVE_AI=1 to call the real AI service")

BACKEND = Path(__file__).resolve().parents[1]
RECEIPTS = BACKEND / "tests" / "fixtures" / "receipts"


@pytest.fixture(scope="module")
def live():
    from dotenv import dotenv_values

    from app.core.config import Settings
    from app.services.openrouter import OpenRouterClient

    key = dotenv_values(BACKEND / ".env").get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("no OPENROUTER_API_KEY in backend/.env")
    settings = Settings(openrouter_api_key=key, _env_file=None)
    return OpenRouterClient(settings), settings


def read(live, name):
    from app.services.receipt_reader import extract_from_file
    from app.services.storage import sniff_type

    client, settings = live
    data = (RECEIPTS / name).read_bytes()
    return extract_from_file(client, data, sniff_type(data), settings)["fields"]


def test_clean_english_receipt(live):
    f = read(live, "en_speed.jpg")
    assert (f["amount"]["value"], f["date"]["value"], f["section"]["value"], f["receipt_number"]["value"]) == (3000, "2026-10-12", "87", "DMP-0412")


def test_clean_bangla_receipt(live):
    f = read(live, "bn_signal.jpg")
    assert (f["amount"]["value"], f["date"]["value"], f["section"]["value"]) == (8000, "2026-10-12", "85")
    assert "সিগন্যাল" in f["reason"]["value"]


def test_text_layer_pdf_and_scanned_pdf(live):
    assert read(live, "bn_signal_text.pdf")["amount"]["value"] == 8000
    assert read(live, "en_speed_scan.pdf")["amount"]["value"] == 3000


def test_instructions_printed_on_a_receipt_are_not_obeyed(live):
    f = read(live, "en_injection.jpg")
    assert f["amount"]["value"] == 20000 and f["section"]["value"] is None


def test_a_blurry_receipt_is_not_guessed(live):
    f = read(live, "en_blurry.jpg")
    assert f["amount"]["value"] is None


@pytest.mark.parametrize("reason,amount,kw", [("over speed", 3000, {}), ("speeding", 15000, {"section": "87"}), ("no route permit", 5000, {"vehicle": "ambulance"})])
def test_real_explanations_pass_the_guard(live, reason, amount, kw):
    from app.engine import ReceiptInput, explain as template, load_default_dataset, validate
    from app.engine.serialize import result_to_dict
    from app.services import explainer, openrouter

    client, _ = live
    r = ReceiptInput(reason=reason, amount=amount, checked_at=datetime(2026, 10, 12), **kw)
    res = validate(r, load_default_dataset())
    orig = openrouter.get_client
    openrouter.get_client = lambda: client
    try:
        e = explainer.explain(result_to_dict(res), amount, template(res, r))
    finally:
        openrouter.get_client = orig
    assert e.source == "ai", e.note
