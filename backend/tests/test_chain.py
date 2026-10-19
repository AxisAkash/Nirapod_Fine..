"""Blockchain audit: dataset fingerprints, anchoring, locks in the database, sealing cases, and detecting tampering."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app import models
from app.services import integrity, sealing
from app.services.datasets import get_active_version
from tests.conftest import auth


def tamper(db, sql, **params):
    """What an attacker with full database access can do: switch the database's own guards off and edit directly."""
    db.execute(text("SET LOCAL session_replication_role = replica"))
    db.execute(text(sql), params)
    db.commit()


def manual(client, headers, **fields):
    r = client.post("/api/cases/manual", json=fields, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def anchored(chain, db):
    """The seeded dataset is anchored on the in-memory chain."""
    version = get_active_version(db)
    assert integrity.anchor_version(db, version) == "anchored"
    db.commit()
    return version


def verify(client, headers, case_id):
    r = client.get(f"/api/cases/{case_id}/verify", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# =============================================================== fingerprints of the rules
OFFENCE_COLUMNS = [
    ("offence_title", "'changed'"), ("offence_description", "'changed'"), ("offence_category", "'changed'"), ("min_fine", "500"),
    ("max_fine", "99999"), ("fine_text", "'Up to Tk 99,999'"), ("imprisonment_text", "'none'"), ("penalty_points", "9"),
    ("repeat_rule_text", "'changed'"), ("source_reference", "'changed'"), ("matchable", "false"), ("is_active", "false"),
    ("fine_tiers", "'[{\"label\": \"x\", \"max_fine\": 1, \"keywords\": []}]'::jsonb"),
]


@pytest.mark.parametrize("column,value", OFFENCE_COLUMNS)
def test_changing_any_column_of_an_offence_rule_changes_the_dataset_fingerprint(db, column, value):
    version = get_active_version(db)
    before = integrity.content_hash(integrity.dataset_leaves(db, version))
    tamper(db, f"UPDATE offence_rules SET {column} = {value} WHERE section_number = '87'")
    db.expire_all()
    assert integrity.content_hash(integrity.dataset_leaves(db, version)) != before, column


EXCEPTION_COLUMNS = [
    ("exception_title", "'changed'"), ("exception_description", "'changed'"), ("applies_to_section", "'87'"),
    ("applies_to_category", "'parking'"), ("conditions", "'{\"effect\": \"exempts\"}'::jsonb"), ("scope_limit", "'Anything goes'"),
    ("required_evidence", "'none'"), ("source_reference", "'changed'"), ("is_active", "false"),
]


@pytest.mark.parametrize("column,value", EXCEPTION_COLUMNS)
def test_changing_any_column_of_an_exception_rule_changes_the_dataset_fingerprint(db, column, value):
    version = get_active_version(db)
    before = integrity.content_hash(integrity.dataset_leaves(db, version))
    tamper(db, f"UPDATE exception_rules SET {column} = {value} WHERE rule_key = 's30-emergency'")
    db.expire_all()
    assert integrity.content_hash(integrity.dataset_leaves(db, version)) != before, column


@pytest.mark.parametrize("sql", [
    "UPDATE offence_aliases SET alias_text = 'something else' WHERE id = (SELECT a.id FROM offence_aliases a JOIN offence_rules r ON r.id = a.offence_rule_id WHERE r.section_number = '87' LIMIT 1)",
    "UPDATE offence_aliases SET language = 'xx' WHERE id = (SELECT a.id FROM offence_aliases a JOIN offence_rules r ON r.id = a.offence_rule_id WHERE r.section_number = '87' LIMIT 1)",
    "UPDATE offence_keywords SET weight = weight + 1 WHERE id = (SELECT k.id FROM offence_keywords k JOIN offence_rules r ON r.id = k.offence_rule_id WHERE r.section_number = '87' LIMIT 1)",
    "UPDATE exception_keywords SET keyword = 'zzz' WHERE id = (SELECT id FROM exception_keywords LIMIT 1)",
    "DELETE FROM offence_aliases WHERE id = (SELECT a.id FROM offence_aliases a JOIN offence_rules r ON r.id = a.offence_rule_id WHERE r.section_number = '87' LIMIT 1)",
    "DELETE FROM offence_rules WHERE section_number = '90'",
    "DELETE FROM exception_rules WHERE rule_key = 's7-disability'",
])
def test_changing_aliases_keywords_or_removing_rules_changes_the_fingerprint(db, sql):
    version = get_active_version(db)
    before = integrity.content_hash(integrity.dataset_leaves(db, version))
    tamper(db, sql)
    db.expire_all()
    assert integrity.content_hash(integrity.dataset_leaves(db, version)) != before


def test_the_fingerprint_is_stable_and_a_clone_has_the_same_one(client, admin_h, db):
    version = get_active_version(db)
    leaves = integrity.dataset_leaves(db, version)
    assert integrity.content_hash(leaves) == integrity.content_hash(dict(reversed(list(leaves.items()))))
    assert len(leaves) == 57
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    assert client.get(f"/api/admin/dataset-versions/{draft['id']}/hash", headers=admin_h).json()["content_hash"] == integrity.content_hash(leaves)


# =============================================================== the database refuses to change locked rules
def must_refuse(db, sql):
    with pytest.raises(DBAPIError) as e:
        db.execute(text(sql))
        db.flush()
    db.rollback()
    assert "locked" in str(e.value) or "cannot" in str(e.value)


@pytest.mark.parametrize("sql", [
    "UPDATE offence_rules SET max_fine = 1 WHERE section_number = '87'",
    "DELETE FROM offence_rules WHERE section_number = '87'",
    "INSERT INTO offence_rules (dataset_version_id, section_number, offence_title, offence_description) SELECT id, '200', 'x', 'x' FROM dataset_versions WHERE status = 'active'",
    "UPDATE exception_rules SET scope_limit = 'anything' WHERE rule_key = 's30-emergency'",
    "DELETE FROM exception_rules WHERE rule_key = 's30-emergency'",
    "UPDATE offence_aliases SET alias_text = 'x' WHERE id = (SELECT id FROM offence_aliases LIMIT 1)",
    "DELETE FROM offence_keywords WHERE id = (SELECT id FROM offence_keywords LIMIT 1)",
    "INSERT INTO offence_keywords (offence_rule_id, keyword, weight) SELECT id, 'new', 5 FROM offence_rules WHERE section_number = '87'",
    "UPDATE exception_keywords SET weight = 99 WHERE id = (SELECT id FROM exception_keywords LIMIT 1)",
    "UPDATE dataset_versions SET version_name = 'renamed' WHERE status = 'active'",
    "UPDATE dataset_versions SET source_hash = 'abc' WHERE status = 'active'",
    "UPDATE dataset_versions SET status = 'draft' WHERE status = 'active'",
    "DELETE FROM dataset_versions WHERE status = 'active'",
])
def test_the_database_refuses_to_change_the_rules_of_an_activated_version(db, sql):
    must_refuse(db, sql)


def test_drafts_stay_editable_and_activation_still_works(client, admin_h, db):
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    rule = next(r for r in client.get("/api/admin/offence-rules", params={"version_id": draft["id"]}, headers=admin_h).json() if r["section_number"] == "87")
    body = {k: rule[k] for k in ("section_number", "offence_title", "min_fine", "aliases", "keywords", "matchable")} | {"max_fine": 4000}
    assert client.put(f"/api/admin/offence-rules/{rule['id']}", json=body, headers=admin_h).status_code == 200
    assert client.delete(f"/api/admin/offence-rules/{rule['id']}", headers=admin_h).status_code == 204
    assert client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h).status_code == 200
    # the old version is archived and now locked too
    must_refuse(db, "UPDATE offence_rules SET max_fine = 1 WHERE section_number = '90' AND dataset_version_id = (SELECT id FROM dataset_versions WHERE status = 'archived')")


def test_an_archived_version_cannot_be_brought_back(client, admin_h, db):
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h)
    must_refuse(db, "UPDATE dataset_versions SET status = 'active' WHERE status = 'archived'")


# =============================================================== anchoring a version
def test_activating_a_version_anchors_it_on_the_chain(client, admin_h, chain, db):
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    v = client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h).json()
    assert v["anchor_status"] == "anchored" and v["anchor_tx_hash"].startswith("0x") and v["anchored_at"]
    anchor = chain.client.get_dataset(integrity.version_key(draft["id"]))
    version = db.get(models.DatasetVersion, draft["id"])
    assert anchor.content_hash == integrity.content_hash(integrity.dataset_leaves(db, version))
    assert anchor.source_hash == version.source_hash and anchor.rule_count == 57


def test_anchoring_twice_writes_once_and_a_different_copy_is_refused_by_the_contract(anchored, chain, db):
    again = integrity.anchor_version(db, anchored, chain.client)
    assert again == "anchored" and chain.w3.eth.get_block("latest")["number"] > 0
    blocks = chain.w3.eth.block_number
    integrity.anchor_version(db, anchored, chain.client)
    assert chain.w3.eth.block_number == blocks  # nothing new was written
    from app.services.chain import ChainError

    with pytest.raises(ChainError) as e:
        chain.client.anchor_dataset(integrity.version_key(anchored.id), "00" * 32, "11" * 32, ["22" * 32], ["33" * 32])
    assert e.value.code == "tx_failed"


def test_activation_works_when_the_chain_is_down_and_the_anchor_can_be_added_later(client, admin_h, chain, db):
    chain.down = True
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    v = client.post(f"/api/admin/dataset-versions/{draft['id']}/activate", headers=admin_h).json()
    assert v["is_active"] and v["anchor_status"] == "pending"
    chain.down = False
    assert client.post(f"/api/admin/dataset-versions/{draft['id']}/anchor", headers=admin_h).json()["anchor_status"] == "anchored"


def test_a_draft_cannot_be_anchored(client, admin_h, chain):
    draft = client.post("/api/admin/dataset-versions", json={"name": "v2"}, headers=admin_h).json()
    assert client.post(f"/api/admin/dataset-versions/{draft['id']}/anchor", headers=admin_h).status_code == 409


def test_only_admins_can_use_the_integrity_endpoints(client, user_h, anchored):
    vid = str(anchored.id)
    assert client.get(f"/api/admin/dataset-versions/{vid}/integrity", headers=user_h).status_code == 403
    assert client.post(f"/api/admin/dataset-versions/{vid}/anchor", headers=user_h).status_code == 403


# =============================================================== checking the rules before using them
def integrity_of(client, admin_h, version):
    return client.get(f"/api/admin/dataset-versions/{version.id}/integrity", headers=admin_h).json()


def test_an_untouched_dataset_verifies(client, admin_h, anchored):
    r = integrity_of(client, admin_h, anchored)
    assert r["status"] == "verified" and r["changed"] == [] and r["content_hash"] == r["anchored_hash"]


@pytest.mark.parametrize("sql,expected", [
    ("UPDATE offence_rules SET max_fine = 99999 WHERE section_number = '87'", {"what": "changed", "name": "Section 87"}),
    ("UPDATE offence_rules SET fine_text = 'Up to Tk 99,999' WHERE section_number = '87'", {"what": "changed", "name": "Section 87"}),
    ("UPDATE exception_rules SET scope_limit = 'Applies to everything' WHERE rule_key = 's30-emergency'", {"what": "changed", "name": "Exception s30-emergency"}),
    ("DELETE FROM offence_rules WHERE section_number = '90'", {"what": "removed", "name": "Section 90"}),
    ("DELETE FROM exception_rules WHERE rule_key = 's7-disability'", {"what": "removed", "name": "Exception s7-disability"}),
])
def test_an_edited_or_removed_rule_is_found_and_named(client, admin_h, anchored, db, sql, expected):
    tamper(db, sql)
    r = integrity_of(client, admin_h, anchored)
    assert r["status"] == "tampered" and r["changed"] == [expected]
    assert expected["name"] in r["message"]


def test_a_rule_added_behind_the_apps_back_is_found(client, admin_h, anchored, db):
    tamper(db, "INSERT INTO offence_rules (dataset_version_id, section_number, offence_title, offence_description, max_fine) SELECT id, '777', 'Sneaky', 'Sneaky', 1 FROM dataset_versions WHERE status = 'active'")
    r = integrity_of(client, admin_h, anchored)
    assert r["status"] == "tampered" and r["changed"] == [{"what": "added", "name": "Section 777"}]


def test_several_changes_are_all_reported(client, admin_h, anchored, db):
    tamper(db, "UPDATE offence_rules SET max_fine = 1 WHERE section_number IN ('87', '90')")
    names = sorted(c["name"] for c in integrity_of(client, admin_h, anchored)["changed"])
    assert names == ["Section 87", "Section 90"]


def test_no_result_is_produced_from_tampered_rules(client, user_h, admin_h, anchored, db):
    tamper(db, "UPDATE offence_rules SET max_fine = 1000000 WHERE section_number = '87'")  # make a huge fine look fine
    r = client.post("/api/cases/manual", json={"reason": "speeding", "amount": 500000}, headers=user_h)
    assert r.status_code == 503
    assert "failed its integrity check" in r.json()["detail"] and "Section 87 changed" in r.json()["detail"]
    assert client.get("/api/cases", headers=user_h).json()["total"] == 0  # nothing half-made is left behind
    tamper(db, "UPDATE offence_rules SET max_fine = 10000 WHERE section_number = '87'")  # put it back
    assert manual(client, user_h, reason="speeding", amount=3000)["validation_status"] == "VALID"


def test_an_unanchored_dataset_still_works_but_says_it_could_not_be_checked(client, user_h, chain):
    body = manual(client, user_h, reason="speeding", amount=3000)
    assert body["validation_status"] == "VALID"
    assert body["analysis"]["dataset_integrity"]["status"] == "unanchored"
    assert "Dataset integrity could not be checked" in body["analysis"]["flags"]


def test_a_verified_dataset_carries_no_warning(client, user_h, anchored):
    body = manual(client, user_h, reason="speeding", amount=3000)
    assert body["analysis"]["dataset_integrity"]["status"] == "verified"
    assert "Dataset integrity could not be checked" not in body["analysis"]["flags"]


def test_an_outage_after_a_successful_check_does_not_stop_or_flag_analyses(client, user_h, anchored, chain):
    manual(client, user_h, reason="speeding", amount=3000)  # the anchor is now remembered (anchors can never change)
    chain.down = True
    body = manual(client, user_h, reason="speeding", amount=4000)
    assert body["analysis"]["dataset_integrity"]["status"] == "verified"


def test_an_outage_before_any_check_is_flagged_but_does_not_stop_analyses(client, user_h, anchored, chain):
    integrity.forget_anchors()
    chain.down = True
    body = manual(client, user_h, reason="speeding", amount=3000)
    assert body["validation_status"] == "VALID" and body["analysis"]["dataset_integrity"]["status"] == "unchecked"
    assert "Dataset integrity could not be checked" in body["analysis"]["flags"]


def test_tampering_cannot_be_hidden_by_an_outage_once_the_anchor_is_known(client, user_h, anchored, chain, db):
    manual(client, user_h, reason="speeding", amount=3000)
    chain.down = True
    tamper(db, "UPDATE offence_rules SET max_fine = 1000000 WHERE section_number = '87'")
    assert client.post("/api/cases/manual", json={"reason": "speeding", "amount": 500000}, headers=user_h).status_code == 503


# =============================================================== recording a case
def test_an_analysed_case_is_recorded_on_the_chain(client, user_h, anchored, chain, db):
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87", vehicle="car")
    audit = body["audit"]
    assert audit["status"] == "sealed" and audit["records"] == 1
    latest = audit["latest"]
    assert latest["transaction_hash"].startswith("0x") and latest["block_number"] > 0 and "chain" in latest["network"]
    on_chain = chain.client.get_case(latest["chain_record_id"])
    assert (on_chain.case_hash, on_chain.dataset_hash, on_chain.result_hash) == (latest["case_hash"], latest["dataset_hash"], latest["result_hash"])


def test_only_the_three_hashes_go_on_the_chain(client, user_h, anchored, chain):
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87", vehicle="car",
                  location="Private Street 12, Dhaka", receipt_number="SECRET-RCPT-77", notes="my private note")
    tx = chain.w3.eth.get_transaction(body["audit"]["latest"]["transaction_hash"])
    data = bytes.fromhex(tx["input"].hex().removeprefix("0x")) if hasattr(tx["input"], "hex") else bytes(tx["input"])
    assert len(data) == 4 + 3 * 32  # a function selector and three 32-byte hashes, nothing else
    for secret in ("Private Street", "SECRET-RCPT", "private note", "speed", "Dhaka", "87", "15000"):
        assert secret.encode() not in data


def test_the_case_fingerprint_is_salted(client, user_h, anchored, db):
    body = manual(client, user_h, reason="speeding", amount=3000)
    rec = db.scalar(select(models.BlockchainRecord))
    case = db.get(models.MamlaCase, body["id"])
    unsalted = sealing.sha256_text(sealing.canonical_json(sealing.case_payload(case)))
    assert rec.salt and len(rec.salt) == 32 and rec.case_hash != unsalted


def test_a_case_is_not_recorded_when_auditing_is_off(client, user_h):
    body = manual(client, user_h, reason="speeding", amount=3000)
    assert body["audit"] == {"enabled": False, "status": "not_recorded", "latest": None, "records": 0}
    assert verify(client, user_h, body["id"])["status"] == "not_recorded"


@pytest.mark.parametrize("make", ["manual", "sample", "upload"])
def test_every_kind_of_case_is_recorded(client, user_h, anchored, make):
    from tests.test_ai import _png

    if make == "manual":
        body = manual(client, user_h, reason="speeding", amount=3000)
    elif make == "sample":
        body = client.post("/api/dummy-url/analyze", json={"scenario": "speed"}, headers=user_h).json()
    else:
        up = client.post("/api/receipts/upload", files={"file": ("r.png", _png(60, 40), "image/png")}, data={"read": "false"}, headers=user_h).json()
        body = client.post(f"/api/cases/{up['case_id']}/analyze", json={"reason": "speeding", "amount": 3000}, headers=user_h).json()
    assert body["audit"]["status"] == "sealed"


# =============================================================== verifying a case
def test_an_untouched_case_verifies(client, user_h, anchored):
    body = manual(client, user_h, reason="speeding", amount=3000)
    v = verify(client, user_h, body["id"])
    assert v["status"] == "verified" and all(r["ok"] for r in v["rows"]) and [r["item"] for r in v["rows"]] == ["Case", "Dataset", "Result"]
    assert all(r["recomputed"] == r["recorded"] == r["on_chain"] for r in v["rows"])
    assert v["history"][0]["current"] is True


def test_a_changed_amount_is_detected_as_case_data_changed(client, user_h, anchored, db):
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87")
    tamper(db, "UPDATE mamla_cases SET extracted_amount = 9000 WHERE id = :id", id=body["id"])
    v = verify(client, user_h, body["id"])
    assert v["status"] == "mismatch" and [r["ok"] for r in v["rows"]] == [False, True, True]
    assert "case data was changed" in v["message"]


def test_a_changed_status_or_explanation_is_detected_as_result_changed(client, user_h, anchored, db):
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87")
    tamper(db, "UPDATE mamla_cases SET validation_status = 'VALID' WHERE id = :id", id=body["id"])
    v = verify(client, user_h, body["id"])
    assert v["status"] == "mismatch" and [r["ok"] for r in v["rows"]] == [True, True, False] and "result" in v["message"]
    tamper(db, "UPDATE mamla_cases SET validation_status = 'INVALID_FINE_TOO_HIGH' WHERE id = :id", id=body["id"])
    assert verify(client, user_h, body["id"])["status"] == "verified"  # putting it back restores the match
    tamper(db, "UPDATE mamla_cases SET ai_explanation = 'This fine is fine.' WHERE id = :id", id=body["id"])
    assert verify(client, user_h, body["id"])["status"] == "mismatch"


def test_a_changed_rule_is_detected_in_an_old_case_and_named(client, user_h, anchored, db):
    body = manual(client, user_h, reason="speeding", amount=3000)
    tamper(db, "UPDATE offence_rules SET max_fine = 99999 WHERE section_number = '87'")
    v = verify(client, user_h, body["id"])
    assert v["status"] == "mismatch" and [r["ok"] for r in v["rows"]] == [True, False, True]
    assert "legal dataset was changed" in v["message"] and "Section 87" in v["message"]
    assert v["dataset_check"]["status"] == "tampered"


def test_covering_your_tracks_in_the_database_does_not_help(client, user_h, anchored, db):
    """An attacker changes the amount AND rewrites the stored hashes to match. The chain still disagrees."""
    body = manual(client, user_h, reason="exceeding speed limit", amount=15000, section="87")
    tamper(db, "UPDATE mamla_cases SET extracted_amount = 9000 WHERE id = :id", id=body["id"])
    db.expire_all()
    case, rec = db.get(models.MamlaCase, body["id"]), db.scalar(select(models.BlockchainRecord))
    rec.case_hash = sealing.salted_case_hash(case, rec.salt)
    db.commit()
    v = verify(client, user_h, body["id"])
    assert v["status"] == "mismatch" and v["rows"][0]["recomputed"] == v["rows"][0]["recorded"] != v["rows"][0]["on_chain"]


def test_a_record_that_is_missing_from_the_chain_is_reported(client, user_h, anchored, chain):
    body = manual(client, user_h, reason="speeding", amount=3000)
    chain.redeploy()  # a new contract: the old records are gone
    v = verify(client, user_h, body["id"])
    assert v["status"] == "not_on_chain" and "reset or replaced" in v["message"]
    chain.wipe()
    assert verify(client, user_h, body["id"])["status"] == "not_on_chain"


def test_verifying_during_an_outage_says_it_could_only_compare_stored_values(client, user_h, anchored, chain):
    body = manual(client, user_h, reason="speeding", amount=3000)
    chain.down = True
    v = verify(client, user_h, body["id"])
    assert v["status"] == "unavailable" and "could not be reached" in v["message"]


# =============================================================== when the chain is not available
def test_an_analysis_still_works_when_the_chain_is_down_and_the_record_can_be_added_later(client, user_h, anchored, chain, db):
    chain.down = True
    body = manual(client, user_h, reason="speeding", amount=3000)
    assert body["validation_status"] == "VALID" and body["audit"]["status"] == "pending"
    assert verify(client, user_h, body["id"])["status"] == "pending"
    chain.down = False
    after = client.post("/api/blockchain/record", json={"case_id": body["id"]}, headers=user_h).json()
    assert after["status"] == "sealed" and after["records"] == 1  # the pending record itself was completed
    assert verify(client, user_h, body["id"])["status"] == "verified"


def test_a_pending_record_for_a_case_that_changed_is_replaced_not_sent_stale(client, user_h, anchored, chain, db):
    chain.down = True
    body = manual(client, user_h, reason="speeding", amount=3000)
    tamper(db, "UPDATE mamla_cases SET extracted_amount = 4000 WHERE id = :id", id=body["id"])
    chain.down = False
    after = client.post("/api/blockchain/record", json={"case_id": body["id"]}, headers=user_h).json()
    assert after["status"] == "sealed" and after["records"] == 2
    assert verify(client, user_h, body["id"])["status"] == "verified"  # it records the case as it is now
    first = db.scalars(select(models.BlockchainRecord).order_by(models.BlockchainRecord.created_at)).first()
    assert first.status == "failed" and "changed before" in first.error


def test_recording_a_sealed_case_again_changes_nothing(client, user_h, anchored, chain):
    body = manual(client, user_h, reason="speeding", amount=3000)
    blocks = chain.w3.eth.block_number
    again = client.post("/api/blockchain/record", json={"case_id": body["id"]}, headers=user_h).json()
    assert again["records"] == 1 and chain.w3.eth.block_number == blocks


# =============================================================== corrections keep the history
def test_a_correction_adds_a_new_record_and_keeps_the_old_one(client, user_h, anchored, chain):
    body = manual(client, user_h, reason="speeding", amount=3000, section="87")
    corrected = client.post(f"/api/cases/{body['id']}/analyze", json={"amount": 15000}, headers=user_h).json()
    assert corrected["audit"]["records"] == 2
    v = verify(client, user_h, body["id"])
    assert v["status"] == "verified" and [h["current"] for h in v["history"]] == [False, True]
    first, second = v["history"]
    assert first["result_hash"] != second["result_hash"] and first["chain_record_id"] != second["chain_record_id"]
    old = chain.client.get_case(first["chain_record_id"])  # the original result is still on the chain, unchanged
    assert old.result_hash == first["result_hash"]


def test_recording_again_without_any_change_uses_a_fresh_salt(client, user_h, anchored):
    body = manual(client, user_h, reason="speeding", amount=3000)
    again = client.post(f"/api/cases/{body['id']}/analyze", headers=user_h).json()
    h = verify(client, user_h, body["id"])["history"]
    assert len(h) == 2 and h[0]["case_hash"] != h[1]["case_hash"]
    assert again["audit"]["status"] == "sealed"


# =============================================================== who can do what
def test_other_users_cannot_verify_or_record_a_case(client, user_h, other_h, admin_h, anchored):
    body = manual(client, user_h, reason="speeding", amount=3000)
    for h in (other_h, admin_h):
        assert client.get(f"/api/cases/{body['id']}/verify", headers=h).status_code == 404
        assert client.post("/api/blockchain/record", json={"case_id": body["id"]}, headers=h).status_code == 404
    assert client.get(f"/api/cases/{body['id']}/verify").status_code == 401
