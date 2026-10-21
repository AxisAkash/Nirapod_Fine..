import hashlib

import pytest
from sqlalchemy import func, select

from app import models
from tests.conftest import JPG, PDF, PNG, auth
from tests.conftest import post_manual


def manual(client, headers, **fields):
    r = post_manual(client, headers, fields)
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
    r = client.post("/api/receipts/upload", files={"file": ("receipt.png", PNG, "image/png")}, headers=user_h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["file_hash"] == hashlib.sha256(PNG).hexdigest() and body["file_type"] == "image/png"
    case = client.get(f"/api/cases/{body['case_id']}", headers=user_h).json()
    assert case["validation_status"] == "PENDING_ANALYSIS"
    assert case["manual_input"] == {}  # nothing is typed in: every detail comes from reading the file
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


def test_analyze_ignores_any_corrections_sent_with_it(client, user_h):
    up = client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).json()
    r = client.post(f"/api/cases/{up['case_id']}/analyze", json={"amount": 9000, "section": "90"}, headers=user_h)
    assert r.status_code == 200
    assert r.json()["extracted"]["amount"] != 9000  # users cannot change a case's details


def test_an_uploaded_but_unanalysed_receipt_is_not_a_recent_check(client, user_h):
    up = client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).json()
    assert client.get("/api/cases", headers=user_h).json() == {"items": [], "total": 0}
    client.post(f"/api/cases/{up['case_id']}/analyze", headers=user_h)
    assert client.get("/api/cases", headers=user_h).json()["total"] == 1


def test_unanalysed_uploads_are_deleted_after_a_day_but_nothing_else(client, user_h, db):
    from datetime import timedelta

    from app import models
    from app.core.config import get_settings
    from app.services.cleanup import purge_unanalysed_uploads

    def upload():
        return client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).json()

    def age(case_id, hours):
        case = db.get(models.MamlaCase, case_id)
        case.created_at = models.utcnow() - timedelta(hours=hours)
        db.commit()

    stale, fresh, done = upload(), upload(), upload()
    client.post(f"/api/cases/{done['case_id']}/analyze", headers=user_h)
    import uuid

    for item, hours in ((stale, 25), (fresh, 2), (done, 48)):
        age(uuid.UUID(item["case_id"]), hours)
    stale_file = get_settings().storage_dir / db.get(models.UploadedReceipt, uuid.UUID(stale["receipt_id"])).file_url
    assert stale_file.exists()

    assert purge_unanalysed_uploads(db) == 1
    db.expire_all()
    assert db.get(models.MamlaCase, uuid.UUID(stale["case_id"])) is None
    assert db.get(models.UploadedReceipt, uuid.UUID(stale["receipt_id"])) is None
    assert not stale_file.exists()
    assert db.get(models.MamlaCase, uuid.UUID(fresh["case_id"])) is not None  # under a day old: kept
    assert db.get(models.MamlaCase, uuid.UUID(done["case_id"])) is not None  # analysed: kept however old


def test_an_unanalysed_case_exposes_what_was_read_from_its_receipt(client, user_h):
    up = client.post("/api/receipts/upload", files={"file": ("a.png", PNG, "image/png")}, headers=user_h).json()
    case = client.get(f"/api/cases/{up['case_id']}", headers=user_h).json()
    reading = case["receipt"]["reading"]
    assert reading["status"] == up["reading"]["status"] and set(reading["fields"]) == set(up["reading"]["fields"])


def test_there_is_no_endpoint_for_typing_a_case_in(client, user_h):
    assert client.post("/api/cases/manual", json={"reason": "speeding", "amount": 3000}, headers=user_h).status_code in (404, 405, 422)


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


# ---------- sample notices (the dashboard's URL card) --------------------------------------------------
def test_sample_scenarios_are_listed_for_the_picker(client, user_h):
    items = client.get("/api/dummy-url/scenarios", headers=user_h).json()
    assert {i["key"] for i in items} >= {"speed", "permit", "park", "signal", "tax"}
    assert all(i["reason"] and i["amount"] for i in items)
    assert client.get("/api/dummy-url/scenarios").status_code == 401


def test_entered_url_is_kept_but_the_chosen_scenario_decides_the_notice(client, user_h):
    url = "https://example.com/traffic-fine-notice/0410"
    body = client.post("/api/dummy-url/analyze", json={"url": url, "scenario": "park"}, headers=user_h).json()
    assert body["dummy_url"] == url and body["extracted"]["reason"] == "parking violation"
    assert body["validation_status"] == "INVALID_FINE_TOO_HIGH"  # Tk 9,000 against the Tk 5,000 parking limit


def test_sample_notice_without_a_url(client, user_h):
    r = client.post("/api/dummy-url/analyze", json={"scenario": "speed"}, headers=user_h)
    assert r.status_code == 201 and r.json()["dummy_url"] is None and r.json()["case_source"] == "dummy_url"


def test_sample_notice_needs_a_url_or_a_scenario_and_rejects_unknown_scenarios(client, user_h):
    assert client.post("/api/dummy-url/analyze", json={}, headers=user_h).status_code == 422
    assert client.post("/api/dummy-url/analyze", json={"scenario": "nope"}, headers=user_h).status_code == 422
    assert client.get("/api/dummy-url/preview", headers=user_h).status_code == 422


def test_case_list_includes_what_the_dashboard_table_shows(client, user_h):
    manual(client, user_h, reason="speeding", amount=3000, receipt_number="DMP-1", location="Dhaka")
    client.post("/api/dummy-url/analyze", json={"url": "https://example.com/n", "scenario": "speed"}, headers=user_h)
    items = {i["case_source"]: i for i in client.get("/api/cases", headers=user_h).json()["items"]}
    assert items["manual_entry"]["receipt_number"] == "DMP-1" and items["manual_entry"]["location"] == "Dhaka"
    assert items["dummy_url"]["dummy_url"] == "https://example.com/n"


def test_justifications_say_which_ones_are_exception_findings(client, user_h):
    body = manual(client, user_h, reason="no route permit", amount=5000, vehicle="ambulance")
    kinds = {j["kind"] for j in body["analysis"]["justifications"]}
    assert kinds == {"check", "exception"}
    leads = ("Exception possible:", "Checked, not applicable:", "Exception claim rejected:", "No exception applies")
    assert all(j["title"].startswith(leads) for j in body["analysis"]["justifications"] if j["kind"] == "exception")
    assert not any(j["title"].startswith(leads) for j in body["analysis"]["justifications"] if j["kind"] == "check")


# ---------- first sign-in: several requests at once must not fight over creating the user ---------------
def test_simultaneous_first_requests_create_the_user_exactly_once(db):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from app.main import app

    def hit(path):
        with TestClient(app, raise_server_exceptions=False) as c:
            return c.get(path, headers=auth("dev:newcomer")).status_code

    paths = ["/api/me", "/api/cases", "/api/me", "/api/offence-rules", "/api/me", "/api/cases", "/api/me", "/api/cases"]
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        codes = list(pool.map(hit, paths))
    assert codes == [200] * len(paths), codes
    assert db.scalar(select(func.count()).select_from(models.User).where(models.User.clerk_user_id == "dev:newcomer")) == 1


def test_losing_the_race_to_create_the_user_returns_the_existing_row(db):
    """Another request created the user between our lookup and our insert: we must use theirs, not crash."""
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core.config import get_settings
    from app.core.security import get_current_user

    existing = models.User(clerk_user_id="dev:racer", email="racer@example.test", full_name="Racer", role="user")
    db.add(existing)
    db.commit()

    class StaleLookup:
        """A session whose first lookup misses, as if the row did not exist yet when we looked."""

        def __init__(self, real):
            self._real, self._missed = real, False

        def scalar(self, *a, **k):
            if not self._missed:
                self._missed = True
                return None
            return self._real.scalar(*a, **k)

        def __getattr__(self, name):
            return getattr(self._real, name)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dev:racer")
    user = get_current_user(creds, StaleLookup(db), get_settings())
    assert user.id == existing.id
    assert db.scalar(select(func.count()).select_from(models.User).where(models.User.clerk_user_id == "dev:racer")) == 1
