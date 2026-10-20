from sqlalchemy import func, select

from app import models
from app.services.datasets import dataset_content_hash, get_active_version, seed_default_dataset
from tests.conftest import auth
from tests.conftest import post_manual


def manual(client, headers, **fields):
    r = post_manual(client, headers, fields)
    assert r.status_code == 201, r.text
    return r.json()


def make_draft(client, admin_h, name="v1.1 draft"):
    r = client.post("/api/admin/dataset-versions", json={"name": name}, headers=admin_h)
    assert r.status_code == 201, r.text
    return r.json()


def rule_id(client, admin_h, version_id, section):
    rules = client.get("/api/admin/offence-rules", params={"version_id": version_id}, headers=admin_h).json()
    return next(r for r in rules if r["section_number"] == section)


# ---------- access -------------------------------------------------------------------------------------------
def test_admin_endpoints_need_the_admin_role(client, user_h):
    for method, path in [("get", "/api/admin/dataset-versions"), ("get", "/api/admin/offence-rules"),
                         ("get", "/api/admin/exception-rules"), ("post", "/api/admin/dataset-versions")]:
        assert getattr(client, method)(path, headers=user_h).status_code == 403, path
    assert client.get("/api/admin/dataset-versions").status_code == 401


def test_admin_lists_the_seeded_version_and_rules(client, admin_h):
    versions = client.get("/api/admin/dataset-versions", headers=admin_h).json()
    assert len(versions) == 1 and versions[0]["status"] == "active" and versions[0]["is_active"]
    assert (versions[0]["offence_rule_count"], versions[0]["exception_rule_count"]) == (42, 15)
    assert len(client.get("/api/admin/offence-rules", headers=admin_h).json()) == 42
    assert len(client.get("/api/admin/exception-rules", headers=admin_h).json()) == 15


# ---------- the active version is read-only ----------------------------------------------------------------
def test_active_version_cannot_be_edited(client, admin_h):
    active = client.get("/api/admin/dataset-versions", headers=admin_h).json()[0]
    rule = rule_id(client, admin_h, active["id"], "87")
    body = {k: rule[k] for k in ("section_number", "offence_title", "min_fine")} | {"max_fine": 99999}
    assert client.put(f"/api/admin/offence-rules/{rule['id']}", json=body, headers=admin_h).status_code == 409
    assert client.delete(f"/api/admin/offence-rules/{rule['id']}", headers=admin_h).status_code == 409
    create = {"dataset_version_id": active["id"], "section_number": "200", "offence_title": "x"}
    assert client.post("/api/admin/offence-rules", json=create, headers=admin_h).status_code == 409


def test_creating_a_draft_clones_everything_and_only_one_draft_is_allowed(client, admin_h):
    draft = make_draft(client, admin_h)
    assert draft["status"] == "draft" and not draft["is_active"]
    assert (draft["offence_rule_count"], draft["exception_rule_count"]) == (42, 15)
    cloned = rule_id(client, admin_h, draft["id"], "87")
    assert len(cloned["aliases"]) >= 9 and len(cloned["keywords"]) >= 5
    assert rule_id(client, admin_h, draft["id"], "82")["fine_tiers"]
    assert client.post("/api/admin/dataset-versions", json={"name": "another"}, headers=admin_h).status_code == 409


def test_draft_version_name_must_be_unique(client, admin_h):
    draft = make_draft(client, admin_h, "v2")
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    assert client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).status_code == 409


# ---------- editing a draft and activating it ---------------------------------------------------------------
def test_editing_a_draft_does_not_change_the_active_version_until_it_is_activated(client, admin_h, user_h):
    draft = make_draft(client, admin_h)
    rule = rule_id(client, admin_h, draft["id"], "87")
    body = {k: rule[k] for k in ("section_number", "offence_title", "min_fine", "aliases", "keywords", "matchable")} | {
        "max_fine": 4000, "offence_category": "speeding"}
    assert client.put(f"/api/admin/offence-rules/{rule['id']}", json=body, headers=admin_h).status_code == 200

    before = manual(client, user_h, reason="speeding", amount=6000)  # still the active version: max 10,000
    assert before["validation_status"] == "VALID"
    old_version = before["dataset"]["id"]

    act = client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    assert act.status_code == 200 and act.json()["is_active"]
    versions = {v["version_name"]: v for v in client.get("/api/admin/dataset-versions", headers=admin_h).json()}
    assert versions["v1.0 RTA 2018 baseline"]["status"] == "archived" and versions["v1.1 draft"]["status"] == "active"

    after = manual(client, user_h, reason="speeding", amount=6000)  # new version: max 4,000
    assert after["validation_status"] == "INVALID_FINE_TOO_HIGH" and after["dataset"]["id"] == draft["id"]
    # the earlier case keeps pointing at the version it was checked against
    assert client.get(f"/api/cases/{before['id']}", headers=user_h).json()["dataset"]["id"] == old_version


def test_added_alias_and_keyword_take_effect_after_activation(client, admin_h, user_h):
    assert manual(client, user_h, reason="zoomed past the camera", amount=1000)["validation_status"] == "NEEDS_MANUAL_REVIEW"
    draft = make_draft(client, admin_h)
    rule = rule_id(client, admin_h, draft["id"], "87")
    body = {k: rule[k] for k in ("section_number", "offence_title", "min_fine", "max_fine", "matchable", "offence_category")}
    body["aliases"] = rule["aliases"] + [{"text": "zoomed past the camera", "language": "en"}]
    body["keywords"] = rule["keywords"]
    assert client.put(f"/api/admin/offence-rules/{rule['id']}", json=body, headers=admin_h).status_code == 200
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    again = manual(client, user_h, reason="zoomed past the camera", amount=1000)
    assert again["validation_status"] == "VALID" and again["matched_rule"]["section"] == "87"


def test_new_rule_can_be_added_to_the_open_draft_without_naming_the_version(client, admin_h):
    draft = make_draft(client, admin_h)
    new = {"section_number": "200", "offence_title": "Test offence", "offence_category": "test", "max_fine": 1000,
           "aliases": [{"text": "test offence", "language": "en"}], "keywords": [{"word": "testing", "weight": 20}]}
    r = client.post("/api/admin/offence-rules", json=new, headers=admin_h)
    assert r.status_code == 201 and r.json()["dataset_version_id"] == draft["id"]
    assert client.post("/api/admin/offence-rules", json=new, headers=admin_h).status_code == 409  # duplicate section
    assert client.delete(f"/api/admin/offence-rules/{r.json()['id']}", headers=admin_h).status_code == 204


def test_new_rule_without_a_draft_is_refused(client, admin_h):
    r = client.post("/api/admin/offence-rules", json={"section_number": "200", "offence_title": "x"}, headers=admin_h)
    assert r.status_code == 409


def test_exception_rules_can_be_added_edited_and_deleted_in_a_draft(client, admin_h, user_h):
    draft = make_draft(client, admin_h)
    new = {"rule_key": "test-ex", "exception_title": "Test exception", "applies_to_category": "parking",
           "effect": "exempts", "vehicle_types": ["tuk tuk"], "scope_limit": "Parking only",
           "keywords": [{"word": "special pass", "weight": 25}]}
    created = client.post("/api/admin/exception-rules", json=new, headers=admin_h)
    assert created.status_code == 201 and created.json()["effect"] == "exempts"
    eid = created.json()["id"]
    assert client.put(f"/api/admin/exception-rules/{eid}", json=new | {"scope_limit": "Changed"}, headers=admin_h).json()["scope_limit"] == "Changed"
    bad = new | {"rule_key": "x", "effect": "made-up"}
    assert client.post("/api/admin/exception-rules", json=bad, headers=admin_h).status_code == 422
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    case = manual(client, user_h, reason="illegal parking", amount=2000, vehicle="tuk tuk")
    assert case["validation_status"] == "VALID_BUT_EXCEPTION_POSSIBLE"
    active = client.get("/api/admin/dataset-versions", headers=admin_h).json()
    assert any(v["is_active"] and v["exception_rule_count"] == 16 for v in active)


def test_an_archived_version_cannot_be_reactivated(client, admin_h):
    old = client.get("/api/admin/dataset-versions", headers=admin_h).json()[0]
    draft = make_draft(client, admin_h)
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    assert client.post(f"/api/admin/dataset-versions/{old['id']}/activate", headers=admin_h).status_code == 409


def test_only_one_version_is_active_at_a_time(client, admin_h, db):
    draft = make_draft(client, admin_h)
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    assert db.scalar(select(func.count()).select_from(models.DatasetVersion).where(models.DatasetVersion.is_active)) == 1


def test_unknown_version_is_404(client, admin_h):
    bogus = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/admin/dataset-versions/{bogus}/activate", headers=admin_h).status_code == 404
    assert client.get("/api/admin/offence-rules", params={"version_id": bogus}, headers=admin_h).status_code == 404


# ---------- audit hash of the dataset content -----------------------------------------------------------
def test_dataset_content_hash_is_stable_and_changes_when_a_rule_changes(client, admin_h, db):
    active = get_active_version(db)
    h1 = dataset_content_hash(db, active)
    assert h1 == dataset_content_hash(db, active)
    assert client.get(f"/api/admin/dataset-versions/{active.id}/hash", headers=admin_h).json()["content_hash"] == h1

    draft = make_draft(client, admin_h)
    assert client.get(f"/api/admin/dataset-versions/{draft['id']}/hash", headers=admin_h).json()["content_hash"] == h1  # clone is identical
    rule = rule_id(client, admin_h, draft["id"], "87")
    body = {k: rule[k] for k in ("section_number", "offence_title", "min_fine", "aliases", "keywords", "matchable")} | {"max_fine": 9999}
    client.put(f"/api/admin/offence-rules/{rule['id']}", json=body, headers=admin_h)
    h2 = client.get(f"/api/admin/dataset-versions/{draft['id']}/hash", headers=admin_h).json()["content_hash"]
    assert h2 != h1
    assert dataset_content_hash(db, active) == h1  # the active version's hash is untouched


def test_seeding_twice_is_harmless(db):
    first = seed_default_dataset(db)
    second = seed_default_dataset(db)
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(models.DatasetVersion)) == 1
    assert db.scalar(select(func.count()).select_from(models.OffenceRule)) == 42


def test_dev_admin_token_variants(client):
    assert client.get("/api/admin/dataset-versions", headers=auth("dev-admin")).status_code == 200
    assert client.get("/api/admin/dataset-versions", headers=auth("dev:admin")).status_code == 403
