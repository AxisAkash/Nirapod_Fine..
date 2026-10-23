"""Tamper-detection experiment for the paper: change a sealed record in the database, then ask whether "Verify" notices.

Run:   EVAL_TAMPER_OUT=../data/eval/results/table_tamper_detection.csv .venv/bin/python -m pytest tests/test_eval_tamper.py -q
Without EVAL_TAMPER_OUT it only asserts that every change is detected. Uses the test database and an in-memory chain.

Each change is made the way an attacker with full database access would make it (database guards switched off), on a
case that was sealed on the chain and verified clean first. The control rows are untouched cases: they must stay
"verified" (a false alarm would count against the system).
"""

import csv
import os
from pathlib import Path

import pytest

from tests.conftest import post_manual
from tests.test_chain import anchored, tamper, verify  # noqa: F401  (fixtures and helpers)

CASE = "UPDATE mamla_cases SET {col} = {val} WHERE id = :id"
RULE = "UPDATE offence_rules SET {col} = {val} WHERE section_number = '87'"

# (what was changed, layer, sql)
CHANGES = [
    ("fine amount on the case", "case", CASE.format(col="extracted_amount", val="1")),
    ("offence reason on the case", "case", CASE.format(col="extracted_reason", val="'something else'")),
    ("section cited on the case", "case", CASE.format(col="extracted_section", val="'90'")),
    ("vehicle type on the case", "case", CASE.format(col="extracted_vehicle_type", val="'ambulance'")),
    ("location on the case", "case", CASE.format(col="extracted_location", val="'elsewhere'")),
    ("claim notes on the case", "case", CASE.format(col="claim_notes", val="'ambulance on emergency duty'")),
    ("verdict: VALID to TOO HIGH", "result", CASE.format(col="validation_status", val="'INVALID_FINE_TOO_HIGH'")),
    ("verdict: set to NEEDS MANUAL REVIEW", "result", CASE.format(col="validation_status", val="'NEEDS_MANUAL_REVIEW'")),
    ("verdict summary text", "result", CASE.format(col="validation_summary", val="'All fine.'")),
    ("explanation text", "result", CASE.format(col="ai_explanation", val="'This fine is fine.'")),
    ("confidence score", "result", CASE.format(col="confidence_score", val="12")),
    ("fine limit of the matched section", "dataset", RULE.format(col="max_fine", val="99999")),
    ("minimum fine of the matched section", "dataset", RULE.format(col="min_fine", val="500")),
    ("fine text of the matched section", "dataset", RULE.format(col="fine_text", val="'Up to Tk 99,999'")),
    ("title of the matched section", "dataset", RULE.format(col="offence_title", val="'changed'")),
    ("imprisonment text of the matched section", "dataset", RULE.format(col="imprisonment_text", val="'none'")),
    ("switch the matched section off", "dataset", RULE.format(col="is_active", val="false")),
    ("limit of an unrelated section (90)", "dataset", "UPDATE offence_rules SET max_fine = 1 WHERE section_number = '90'"),
    ("an exception rule's scope limit", "dataset", "UPDATE exception_rules SET scope_limit = 'changed' WHERE rule_key = 's30-emergency'"),
    ("an exception rule's required evidence", "dataset", "UPDATE exception_rules SET required_evidence = 'none needed' WHERE rule_key = 's30-emergency'"),
    ("a new keyword for the matched section", "dataset", "INSERT INTO offence_keywords (offence_rule_id, keyword, weight) SELECT id, 'sneaky', 50 FROM offence_rules WHERE section_number = '87'"),
    ("an alias removed from the matched section", "dataset", "DELETE FROM offence_aliases WHERE id = (SELECT a.id FROM offence_aliases a JOIN offence_rules r ON r.id = a.offence_rule_id WHERE r.section_number = '87' LIMIT 1)"),
    ("a whole section deleted", "dataset", "DELETE FROM offence_rules WHERE section_number = '66'"),
    ("a new section added", "dataset", "INSERT INTO offence_rules (dataset_version_id, section_number, offence_title, offence_description, max_fine) SELECT id, '777', 'Sneaky', 'Sneaky', 1 FROM dataset_versions WHERE status = 'active'"),
]
RESULTS: list[dict] = []


def sealed_case(client, headers):
    body = post_manual(client, headers, {"reason": "exceeding speed limit", "amount": 3000, "section": "87"}).json()
    assert verify(client, headers, body["id"])["status"] == "verified"
    return body["id"]


@pytest.mark.parametrize("label,layer,sql", CHANGES, ids=[c[0] for c in CHANGES])
def test_change_is_detected(client, user_h, anchored, chain, db, label, layer, sql):  # noqa: F811
    case_id = sealed_case(client, user_h)
    tamper(db, sql, **({"id": case_id} if ":id" in sql else {}))
    status = verify(client, user_h, case_id)["status"]
    RESULTS.append(dict(change=label, layer=layer, kind="tampered", detected=status != "verified", verify_status=status))
    assert status != "verified"


@pytest.mark.parametrize("n", range(8))
def test_untouched_case_is_not_flagged(client, user_h, anchored, chain, n):  # noqa: F811
    case_id = sealed_case(client, user_h)
    status = verify(client, user_h, case_id)["status"]
    RESULTS.append(dict(change=f"no change (control {n + 1})", layer="control", kind="control", detected=status != "verified", verify_status=status))
    assert status == "verified"


def test_zz_write_table():
    target = os.environ.get("EVAL_TAMPER_OUT")
    if not target:
        pytest.skip("EVAL_TAMPER_OUT not set")
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=["change", "layer", "kind", "detected", "verify_status"])
        w.writeheader()
        w.writerows(RESULTS)
    tampered = [r for r in RESULTS if r["kind"] == "tampered"]
    controls = [r for r in RESULTS if r["kind"] == "control"]
    print(f"\ntampering detected: {sum(r['detected'] for r in tampered)}/{len(tampered)}; false alarms: {sum(r['detected'] for r in controls)}/{len(controls)}")
