from datetime import datetime

import pytest

from app.engine import PriorCase, ReceiptInput, Status, explain, load_default_dataset, validate

DS = load_default_dataset()
NOW = datetime(2026, 10, 12, 12, 0)


def run(reason, amount=None, section=None, vehicle=None, notes=None, history=()):
    return validate(ReceiptInput(reason, amount, section, vehicle, notes, checked_at=NOW), DS, history)


# ---- the worked examples from the design ----------------------------------------------------------
def test_speeding_first_offence_is_valid():
    r = run("over speed", 3000, vehicle="motorcycle")
    assert r.status is Status.VALID
    assert r.matched_rule.section == "87" and r.allowed_fine == 10_000 and r.occurrence == 1


def test_speeding_above_maximum_is_too_high():
    r = run("exceeding speed limit", 15_000, section="87", vehicle="car")
    assert r.status is Status.INVALID_FINE_TOO_HIGH and r.allowed_fine == 10_000


def test_repeat_offence_allows_double_the_previous_fine():
    prior = [PriorCase("87", 3000, datetime(2026, 9, 28))]
    r = run("speeding", 7000, section="87", history=prior)
    assert r.status is Status.INVALID_FINE_TOO_HIGH
    assert (r.allowed_fine, r.previous_fine, r.occurrence) == (6000, 3000, 2)
    assert "Repeat offence" in r.flags
    assert run("speeding", 6000, section="87", history=prior).status is Status.VALID


def test_repeat_allowed_fine_is_capped_at_maximum():
    prior = [PriorCase("87", 8000, datetime(2026, 9, 28))]
    r = run("speeding", 10_000, history=prior)
    assert r.allowed_fine == 10_000 and r.status is Status.VALID


def test_repeat_uses_the_most_recent_prior_fine_for_the_same_section_only():
    prior = [PriorCase("87", 1000, datetime(2026, 1, 1)), PriorCase("87", 3000, datetime(2026, 9, 1)),
             PriorCase("90", 4000, datetime(2026, 10, 1))]
    r = run("speeding", 6000, history=prior)
    assert (r.previous_fine, r.allowed_fine, r.occurrence) == (3000, 6000, 3)


def test_prior_cases_after_the_check_time_are_ignored():
    prior = [PriorCase("87", 3000, datetime(2026, 11, 1))]
    assert run("speeding", 9000, history=prior).allowed_fine == 10_000


def test_cited_section_that_contradicts_the_reason_is_a_mismatch():
    r = run("illegal parking", 2000, section="87", vehicle="car")
    assert r.status is Status.INVALID_REASON_MISMATCH
    assert r.matched_rule.section == "90" and r.cited_rule.section == "87"


def test_ambulance_without_route_permit_may_be_exempt():
    r = run("no route permit", 5000, vehicle="ambulance")
    assert r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE and r.matched_rule.section == "77"
    assert any(e.applies and e.key == "s30-emergency" for e in r.exceptions)


def test_emergency_claim_does_not_excuse_speeding():
    r = run("speeding", 4000, vehicle="ambulance", notes="rushing patient to hospital")
    assert r.status is Status.INVALID_EXCEPTION_NOT_APPLICABLE
    assert any(e.key == "none-emergency" and e.claimed and not e.applies for e in r.exceptions)
    # the route-permit exemption is noted but does not apply to speeding
    assert any(e.key == "s30-emergency" and e.informational for e in r.exceptions)


def test_ambulance_vehicle_alone_does_not_make_a_speeding_ticket_invalid():
    r = run("speeding", 4000, vehicle="ambulance")
    assert r.status is Status.VALID


def test_bangla_receipt_with_bangla_section_number():
    r = run("ট্রাফিক সিগন্যাল অমান্য", 8000, section="ধারা ৮৫", vehicle="bus")
    assert r.status is Status.VALID and r.matched_rule.section == "85"


def test_extortion_has_no_ceiling_so_needs_manual_review():
    r = run("চাঁদাবাজি", 20_000, vehicle="truck")
    assert r.status is Status.NEEDS_MANUAL_REVIEW and r.matched_rule.section == "83"
    assert "no Taka ceiling" in r.manual_reason


# ---- edge cases ---------------------------------------------------------------------------------------
def test_fine_too_high_takes_precedence_over_exception_but_keeps_a_flag():
    r = run("no route permit", 50_000, vehicle="ambulance")
    assert r.status is Status.INVALID_FINE_TOO_HIGH and "Exception possible" in r.flags


def test_unknown_offence_needs_manual_review():
    assert run("flying a kite", 1000).status is Status.NEEDS_MANUAL_REVIEW


def test_missing_amount_needs_manual_review():
    assert run("speeding", None).status is Status.NEEDS_MANUAL_REVIEW


def test_amount_below_statutory_minimum_needs_manual_review():
    r = run("fake number plate", 5000)
    assert r.matched_rule.section == "73" and r.status is Status.NEEDS_MANUAL_REVIEW
    assert "minimum" in r.manual_reason


def test_cited_section_missing_from_dataset_needs_manual_review():
    r = run("speeding", 1000, section="999")
    assert r.status is Status.NEEDS_MANUAL_REVIEW and "not in the active dataset" in r.manual_reason


def test_supporting_provisions_cannot_be_checked_as_offences():
    r = run("speeding", 1000, section="100")
    assert r.status is Status.NEEDS_MANUAL_REVIEW and "supporting provision" in r.manual_reason
    assert all(c.rule.section not in {"99", "100"} for c in r.candidates)


def test_cited_section_with_unsupported_reason_needs_manual_review():
    assert run("flying a kite", 1000, section="87").status is Status.NEEDS_MANUAL_REVIEW


def test_cited_parent_section_picks_the_best_matching_subsection():
    r = run("defective brake", 5000, section="89")
    assert r.matched_rule.section == "89(2)" and r.status is Status.VALID


def test_horn_offence_by_an_ambulance_may_be_exempt_with_an_approved_horn():
    r = run("illegal horn", 2000, vehicle="ambulance")
    assert r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE and r.matched_rule.section == "88"


def test_natural_calamity_is_permission_based_for_route_permit():
    r = run("no route permit", 5000, notes="diverted because of flood")
    assert r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE
    assert "prior permission" in next(e for e in r.exceptions if e.applies).reason


def test_repealed_ordinance_claim_is_rejected():
    r = run("illegal parking", 2000, notes="allowed under the motor vehicles ordinance 1983")
    assert r.status is Status.INVALID_EXCEPTION_NOT_APPLICABLE


def test_vip_status_is_not_an_exemption():
    assert run("red light", 5000, notes="VIP convoy").status is Status.INVALID_EXCEPTION_NOT_APPLICABLE


def test_candidates_are_ranked_and_keep_scoring_signals():
    r = run("speeding", 3000)
    assert r.candidates[0].rule.section == "87"
    assert r.candidates == sorted(r.candidates, key=lambda c: c.total, reverse=True)
    assert any("alias" in w for w in r.candidates[0].why)


def test_every_result_has_a_summary_and_justification():
    for args in [("over speed", 3000), ("flying a kite", 1), ("illegal parking", 2000, "87")]:
        r = run(*args)
        assert r.summary and r.justifications and explain(r, ReceiptInput(args[0], args[1]))


def test_engine_result_does_not_depend_on_input_order_or_mutate_the_dataset():
    before = [len(x.aliases) for x in DS.rules]
    run("speeding", 3000)
    assert before == [len(x.aliases) for x in DS.rules]


@pytest.mark.parametrize("reason,section", [
    ("exceeding speed limit", "87"), ("illegal parking", "90"), ("no tax token", "76"), ("no helmet", "92(1)"),
    ("overloaded truck", "86"), ("reckless driving", "105"), ("no fitness certificate", "75"),
    ("unregistered vehicle", "72"), ("fare chart not displayed", "80"), ("black smoke", "89(1)"),
])
def test_common_offences_resolve_to_the_expected_section(reason, section):
    assert run(reason, 1000).matched_rule.section == section


# ---- Section 82 fine tiers --------------------------------------------------------------------------
def test_section_82_temporary_structure_uses_the_lower_ceiling():
    r = run("illegal structure beside highway", 60_000, notes="temporary tin shed")
    assert r.matched_rule.section == "82" and r.tier_label == "temporary structure"
    assert r.status is Status.INVALID_FINE_TOO_HIGH and r.allowed_fine == 50_000


def test_section_82_permanent_structure_uses_the_higher_ceiling():
    r = run("illegal structure beside highway", 300_000, notes="permanent pucca building")
    assert r.tier_label == "permanent structure" and r.allowed_fine == 500_000 and r.status is Status.VALID


def test_section_82_without_a_tier_is_valid_when_below_the_lower_ceiling():
    r = run("illegal structure beside highway", 40_000)
    assert r.status is Status.VALID and r.tier_label is None


def test_section_82_without_a_tier_needs_review_between_the_two_ceilings():
    r = run("illegal structure beside highway", 60_000)
    assert r.status is Status.NEEDS_MANUAL_REVIEW
    assert "lower ceiling of Tk 50,000" in r.manual_reason


def test_section_82_above_the_higher_ceiling_is_too_high_even_without_a_tier():
    assert run("illegal structure beside highway", 600_000).status is Status.INVALID_FINE_TOO_HIGH


def test_section_82_bangla_tier_words():
    r = run("মহাসড়কের পাশে অবৈধ স্থাপনা", 60_000, notes="অস্থায়ী দোকান")
    assert r.tier_label == "temporary structure" and r.status is Status.INVALID_FINE_TOO_HIGH


# ---- Bangla receipts ----------------------------------------------------------------------------------
@pytest.mark.parametrize("reason,section,min_conf", [
    ("ট্রাফিক সিগন্যাল অমান্য", "85", 60), ("অতিরিক্ত গতিতে গাড়ি চালানো", "87", 60),
    ("নিষিদ্ধ স্থানে পার্কিং", "90", 60), ("হেলমেট ছাড়া মোটরসাইকেল চালানো", "92(1)", 60),
    ("ট্যাক্স টোকেন নেই", "76", 60), ("ফিটনেস সনদ ছাড়া", "75", 60), ("রুট পারমিট ছাড়া", "77", 60),
    ("বেপরোয়া গাড়ি চালানো", "105", 60), ("অতিরিক্ত ওজন", "86", 60), ("হাইড্রোলিক হর্ন", "88", 60),
])
def test_bangla_offence_text_resolves_confidently(reason, section, min_conf):
    r = run(reason, 1000)
    assert r.matched_rule.section == section
    assert r.confidence >= min_conf


def test_bangla_spelling_variants_normalise_to_the_same_text():
    from app.engine.normalize import normalize

    composed, decomposed = "ড়ঢ়", "ড়ঢ়"  # ড় ঢ় as single vs combining forms
    assert normalize(composed) == normalize(decomposed)


def test_bangla_emergency_claim_is_rejected():
    r = run("গতিসীমা অতিক্রম", 4000, vehicle="অ্যাম্বুলেন্স", notes="রোগী নিয়ে হাসপাতালে যাচ্ছিলাম")
    assert r.status is Status.INVALID_EXCEPTION_NOT_APPLICABLE


def test_bangla_ambulance_vehicle_triggers_the_route_permit_exemption():
    r = run("রুট পারমিট ছাড়া", 5000, vehicle="অ্যাম্বুলেন্স")
    assert r.status is Status.VALID_BUT_EXCEPTION_POSSIBLE


# ---- other fixes -------------------------------------------------------------------------------------
def test_imprisonment_sections_carry_a_flag_and_a_justification():
    r = run("reckless driving", 100_000)
    assert "Imprisonment also possible" in r.flags
    assert any(j.title == "Imprisonment may also apply" for j in r.justifications)


def test_result_serialises_to_json_safe_dict():
    import json

    from app.engine.serialize import result_to_dict

    d = result_to_dict(run("speeding", 15_000))
    assert d["status"] == "INVALID_FINE_TOO_HIGH" and d["matched_section"] == "87" and d["allowed_fine"] == 10_000
    json.dumps(d)  # must not raise
