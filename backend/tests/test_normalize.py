import pytest

from app.engine.normalize import contains, normalize, parse_section


@pytest.mark.parametrize("text,expected", [
    ("Section 87", "87"), ("section 89 (1)", "89(1)"), ("89(2)", "89(2)"), ("s.85", "85"), ("87", "87"),
    ("ধারা ৮৭", "87"), ("ধারা ৮৯(২)", None), ("Section 7", None), ("", None), (None, None), ("abc", None),
])
def test_parse_section(text, expected):
    # '89(২)' only converts digits; sub-section 2 is accepted after conversion
    if text == "ধারা ৮৯(২)":
        expected = "89(2)"
    assert parse_section(text) == expected


def test_normalize_converts_bangla_digits_and_strips_punctuation():
    assert normalize("  Over-Speed!! ৮৭ ") == "over speed 87"


def test_normalize_keeps_bangla_vowel_signs():
    assert normalize("সিগন্যাল অমান্য") == "সিগন্যাল অমান্য"


def test_contains_uses_word_boundary_for_short_terms():
    assert contains("rash driving", "rash")
    assert not contains("car crash on highway", "rash")
    assert not contains("urban road", "ban")
    assert contains("speeding on road", "speed")


def test_contains_uses_substring_for_long_terms_and_bangla():
    assert contains("overloaded truck", "overload")
    assert contains("চাঁদাবাজি করা", "চাঁদাবাজি")
