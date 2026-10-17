import hashlib

import pytest
from sqlalchemy import func, select

from app import models
from tests.conftest import JPG, PDF, PNG, auth


def manual(client, headers, **fields):
    r = client.post("/api/cases/manual", json=fields, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- authentication --------------------------------------------------------------------------
def test_requests_without_a_token_are_rejected(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/health").status_code == 200  # health stays public


def test_invalid_dev_token_is_rejected(client):
    assert client.get("/api/me", headers=auth("nope")).status_code == 401


def test_me_creates_the_local_user_and_reads_the_role(client, user_h, admin_h):
    me = client.get("/api/me", headers=user_h).json()
    assert me["role"] == "user" and me["email"] == "dev-user@example.test"
    assert client.get("/api/me", headers=admin_h).json()["role"] == "admin"
    assert client.get("/api/me", headers=user_h).json()["id"] == me["id"]  # same row on the second call


# ---------- receipts ---------------------------------------------------------------------------------
def test_upload_stores_the_file_hashes_it_and_opens_a_pending_case(client, user_h):
    r = client.post("/api/receipts/upload", files={"file": ("receipt.png", PNG, "image/png")},
                    data={"reason": "over speed", "amount": "3000"}, headers=user_h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["file_hash"] == hashlib.sha256(PNG).hexdigest() and body["file_type"] == "image/png"
    case = client.get(f"/api/cases/{body['case_id']}", headers=user_h).json()
    assert case["validation_status"] == "PENDING_ANALYSIS"
    assert case["manual_input"] == {"reason": "over speed", "amount": "3000"}
    assert case["receipt"]["file_hash"] == body["file_hash"]


@pytest.mark.parametrize("content,name", [(JPG, "a.jpg"), (PDF, "a.pdf")])
def test_upload_accepts_jpg_and_pdf(client, user_h, content, name):
    r = client.post("/api/receipts/upload", files={"file": (name, content, "application/octet-stream")}, headers=user_h)
    assert r.status_code == 201


def test_upload_decides_the_type_from_the_bytes_not_the_filename(client, user_h):
    r = client.post("/api/receipts/upload", files={"file": ("receipt.png", b"MZ not an image at all", "image/png")}, headers=user_h)
    assert r.status_code == 415


def test_upload_rejects_empty_and_oversized_files(client, user_h, monkeypatch):
    assert client.post("/api/receipts/upload", files={"file": ("e.png", b"", "image/png")}, headers=user_h).status_code == 400
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).status_code == 413


def test_receipt_file_is_downloadable_only_by_its_owner(client, user_h, other_h):
    up = client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).json()
    ok = client.get(f"/api/receipts/{up['receipt_id']}/file", headers=user_h)
    assert ok.status_code == 200 and ok.content == PNG
    assert client.get(f"/api/receipts/{up['receipt_id']}/file", headers=other_h).status_code == 404


def test_upload_then_analyze_with_corrections(client, user_h):
    up = client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")},
                     data={"reason": "illegal parking", "amount": "2000"}, headers=user_h).json()
    r = client.post(f"/api/cases/{up['case_id']}/analyze", json={"amount": 9000, "section": "90"}, headers=user_h)
    assert r.status_code == 200
    body = r.json()
    assert body["validation_status"] == "INVALID_FINE_TOO_HIGH"  # the correction (9000) replaced the typed 2000
    assert body["extracted"]["amount"] == 9000 and body["matched_rule"]["section"] == "90"


# ---------- analysis --------------------------------------------------------------------------------------
def test_manual_case_is_analysed_and_every_part_is_stored(client, user_h, db):
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87", vehicle="car")
    assert body["validation_status"] == "INVALID_FINE_TOO_HIGH"
    assert body["matched_rule"]["section"] == "87" and body["matched_rule"]["max_fine"] == 10000
    assert body["analysis"]["allowed_fine"] == 10000 and body["dataset"]["name"].startswith("v1.0")
    assert body["matches"][0]["section"] == "87" and len(body["matches"]) >= 2
    assert body["ai_explanation"] and body["confidence_score"] > 0
    case = db.scalar(select(models.MamlaCase))
    assert case.extracted_amount == 15000 and case.matched_rule.section_number == "87"
    assert case.validation_summary and case.analysis_details["status"] == "INVALID_FINE_TOO_HIGH"


def test_exception_checks_are_stored(client, user_h, db):
    body = manual(client, user_h, reason="no route permit", amount=5000, vehicle="ambulance")
    assert body["validation_status"] == "VALID_BUT_EXCEPTION_POSSIBLE"
    assert any(e["applies"] and e["key"] == "s30-emergency" for e in body["exception_checks"])
    assert db.scalar(select(func.count()).select_from(models.MamlaExceptionCheck)) >= 1


def test_section_82_tier_is_applied_through_the_api(client, user_h):
    high = manual(client, user_h, reason="illegal structure beside highway", amount=60000, notes="temporary shed")
    assert high["validation_status"] == "INVALID_FINE_TOO_HIGH" and high["analysis"]["tier"] == "temporary structure"
    unclear = manual(client, user_h, reason="illegal structure beside highway", amount=60000)
    assert unclear["validation_status"] == "NEEDS_MANUAL_REVIEW"


def test_bangla_amount_digits_are_understood(client, user_h):
    body = manual(client, user_h, reason="speeding", amount="৩,০০০")
    assert body["extracted"]["amount"] == 3000 and body["validation_status"] == "VALID"


def test_missing_reason_goes_to_manual_review_instead_of_failing(client, user_h):
    assert manual(client, user_h, amount=1000)["validation_status"] == "NEEDS_MANUAL_REVIEW"


# ---------- repeat offences ---------------------------------------------------------------------------------
def test_repeat_offence_doubles_the_previous_fine_and_caps_at_the_maximum(client, user_h):
    first = manual(client, user_h, reason="speeding", amount=3000, section="87")
    assert first["analysis"]["occurrence"] == 1 and first["analysis"]["allowed_fine"] == 10000
    second = manual(client, user_h, reason="speeding", amount=7000, section="87")
    assert second["analysis"]["allowed_fine"] == 6000 and second["analysis"]["previous_fine"] == 3000
    assert second["analysis"]["occurrence"] == 2 and second["validation_status"] == "INVALID_FINE_TOO_HIGH"
    third = manual(client, user_h, reason="speeding", amount=6000, section="87")
    assert third["validation_status"] == "VALID"  # the too-high case did not count; previous is still 3000
    fourth = manual(client, user_h, reason="speeding", amount=10000, section="87")
    assert fourth["analysis"]["allowed_fine"] == 10000  # 6000 x 2 = 12000, capped at the maximum


def test_history_is_per_user_and_per_section(client, user_h, other_h):
    manual(client, user_h, reason="speeding", amount=3000)
    assert manual(client, other_h, reason="speeding", amount=9000)["validation_status"] == "VALID"
    assert manual(client, user_h, reason="illegal parking", amount=4000)["analysis"]["occurrence"] == 1


def test_analysing_again_replaces_results_and_never_double_counts(client, user_h, db):
    case = manual(client, user_h, reason="speeding", amount=3000)
    for _ in range(3):
        assert client.post(f"/api/cases/{case['id']}/analyze", headers=user_h).status_code == 200
    assert db.scalar(select(func.count()).select_from(models.MamlaHistory)) == 1
    assert db.scalar(select(func.count()).select_from(models.MamlaCaseMatch)) == len(
        client.get(f"/api/cases/{case['id']}", headers=user_h).json()["matches"])
    nxt = manual(client, user_h, reason="speeding", amount=5000)
    assert nxt["analysis"]["occurrence"] == 2 and nxt["analysis"]["allowed_fine"] == 6000
    again = client.post(f"/api/cases/{case['id']}/analyze", headers=user_h).json()
    assert again["analysis"]["occurrence"] == 1  # a later case never changes an earlier one


def test_correcting_a_case_updates_the_history_row(client, user_h, db):
    case = manual(client, user_h, reason="speeding", amount=3000)
    client.post(f"/api/cases/{case['id']}/analyze", json={"amount": 4000}, headers=user_h)
    assert db.scalar(select(models.MamlaHistory.fine_amount)) == 4000


# ---------- ownership -----------------------------------------------------------------------------------------
def test_users_cannot_see_or_touch_each_others_cases(client, user_h, other_h):
    case = manual(client, user_h, reason="speeding", amount=3000)
    assert client.get(f"/api/cases/{case['id']}", headers=other_h).status_code == 404
    assert client.post(f"/api/cases/{case['id']}/analyze", headers=other_h).status_code == 404
    assert client.get("/api/cases", headers=other_h).json() == {"items": [], "total": 0}
    assert client.get("/api/cases", headers=user_h).json()["total"] == 1


def test_admins_do_not_get_access_to_other_users_cases(client, user_h, admin_h):
    case = manual(client, user_h, reason="speeding", amount=3000)
    assert client.get(f"/api/cases/{case['id']}", headers=admin_h).status_code == 404


def test_case_list_filters_by_status_and_paginates(client, user_h):
    manual(client, user_h, reason="speeding", amount=3000)
    manual(client, user_h, reason="illegal parking", amount=9000)
    manual(client, user_h, reason="illegal parking", amount=1000)
    all_ = client.get("/api/cases", headers=user_h).json()
    assert all_["total"] == 3 and all_["items"][0]["created_at"] >= all_["items"][-1]["created_at"]
    only = client.get("/api/cases?status=INVALID_FINE_TOO_HIGH", headers=user_h).json()
    assert only["total"] == 1 and only["items"][0]["section"] == "90"
    assert len(client.get("/api/cases?limit=2&offset=2", headers=user_h).json()["items"]) == 1


def test_unknown_case_id_is_404(client, user_h):
    assert client.get("/api/cases/00000000-0000-0000-0000-000000000000", headers=user_h).status_code == 404
    assert client.get("/api/cases/not-a-uuid", headers=user_h).status_code == 422


# ---------- dummy URL and rules ---------------------------------------------------------------------------
def test_dummy_url_preview_and_analysis(client, user_h):
    url = "https://mamla.example.gov.bd/case/permit-0410"
    pre = client.get("/api/dummy-url/preview", params={"url": url}, headers=user_h).json()
    assert pre["reason"] == "no route permit" and pre["vehicle"] == "ambulance"
    r = client.post("/api/dummy-url/analyze", json={"url": url}, headers=user_h)
    assert r.status_code == 201
    body = r.json()
    assert body["case_source"] == "dummy_url" and body["dummy_url"] == url
    assert body["validation_status"] == "VALID_BUT_EXCEPTION_POSSIBLE"
    assert client.get("/api/dummy-url/preview", params={"url": url}, headers=user_h).json() == pre  # repeatable


def test_offence_rules_list_and_search(client, user_h):
    body = client.get("/api/offence-rules", headers=user_h).json()
    assert len(body["items"]) == 42 and body["items"][0]["section_number"] == "66"
    sections = [r["section_number"] for r in body["items"]]
    assert sections.index("89(1)") < sections.index("89(2)") < sections.index("90")
    found = client.get("/api/offence-rules", params={"q": "parking"}, headers=user_h).json()["items"]
    assert [r["section_number"] for r in found] == ["90"]
    assert client.get("/api/offence-rules").status_code == 401
