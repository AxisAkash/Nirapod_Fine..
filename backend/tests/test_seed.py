"""Independent check of the seed against figures written out from the fines PDF."""
from app.engine import load_default_dataset

LAKH = 100_000
# section -> (min, max); None max = the PDF states no numeric ceiling
FROM_PDF = {
    "66": (0, 25_000), "67": (0, 5_000), "68": (0, 30_000), "69": (LAKH, 5 * LAKH), "70": (0, 25_000),
    "71": (0, 5_000), "72": (0, 50_000), "73": (LAKH, 5 * LAKH), "74": (0, 5_000), "75": (0, 25_000),
    "76": (0, 10_000), "77": (0, 20_000), "78": (0, 30_000), "79": (0, 25_000), "80": (0, 10_000),
    "81": (0, 50_000), "82": (0, 5 * LAKH), "83": (0, None), "84": (0, 3 * LAKH), "85": (0, 10_000),
    "86": (0, LAKH), "87": (0, 10_000), "88": (0, 10_000), "89(1)": (0, 25_000), "89(2)": (0, 20_000),
    "90": (0, 5_000), "91": (0, 5_000), "92(1)": (0, 10_000), "92(2)": (0, 5_000), "93": (0, 25_000),
    "94": (0, None), "95": (0, 20_000), "96": (0, LAKH), "97": (25_000, LAKH), "98": (0, 3 * LAKH),
    "99": (0, None), "100": (0, None), "101": (0, 10_000), "102": (0, 10_000), "103": (0, 10_000),
    "104": (0, 20_000), "105": (0, 5 * LAKH),
}
DS = load_default_dataset()


def test_every_section_in_the_pdf_is_seeded_exactly_once():
    sections = [r.section for r in DS.rules]
    assert len(sections) == len(set(sections)) == len(FROM_PDF) == 42
    assert set(sections) == set(FROM_PDF)


def test_fine_limits_match_the_pdf():
    for r in DS.rules:
        assert (r.min_fine, r.max_fine) == FROM_PDF[r.section], r.section


def test_only_99_and_100_are_not_matchable():
    assert {r.section for r in DS.rules if not r.matchable} == {"99", "100"}


def test_every_matchable_rule_has_aliases_and_keywords_and_a_source():
    for r in DS.rules:
        assert r.aliases and r.keywords and r.source_reference and r.fine_text, r.section


def test_commonly_cited_sections_have_bangla_aliases():
    for s in ("66", "72", "75", "76", "77", "85", "86", "87", "90", "105"):
        assert any(any("ঀ" <= ch <= "৿" for ch in a) for a in DS.rule_for_section(s).aliases), s


def test_imprisonment_is_recorded_for_73_and_105():
    assert DS.rule_for_section("73").imprisonment_text and DS.rule_for_section("105").imprisonment_text


def test_exception_rules_have_known_effects_and_scope_limits():
    assert len(DS.exceptions) == 15
    keys = [x.key for x in DS.exceptions]
    assert len(keys) == len(set(keys))
    for x in DS.exceptions:
        assert x.effect in {"exempts", "permission_based", "no_general_exemption", "repealed"}, x.key
        assert x.scope_limit and x.source_reference and x.keywords, x.key


def test_route_permit_exemptions_are_limited_to_route_permit():
    for x in DS.exceptions:
        if x.key.startswith("s30-"):
            assert x.category == "route_permit"


def test_every_exception_category_names_a_real_offence_category_or_wildcard():
    categories = {r.category for r in DS.rules} | {"*"}
    for x in DS.exceptions:
        assert x.category in categories, x.key
        if x.section:
            assert DS.rule_for_section(x.section), x.key
