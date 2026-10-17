"""Text normalisation shared by retrieval and exception matching."""
from __future__ import annotations

import re
import unicodedata

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_SECTION = re.compile(r"(?:section|sec\.?|s\.|ধারা)\s*(\d{2,3})\s*(?:\(\s*([12])\s*\))?", re.IGNORECASE)
_BARE_SECTION = re.compile(r"^\s*(\d{2,3})\s*(?:\(\s*([12])\s*\))?\s*$")


def normalize(text: str | None) -> str:
    """Lower-case, convert Bangla digits, drop punctuation, collapse spaces.

    Combining marks are kept: Bangla vowel signs are marks and removing them would break words.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text).translate(_BN_DIGITS).lower()
    kept = []
    for ch in text:
        if ch.isalnum() or ch == "/" or ch.isspace() or unicodedata.category(ch).startswith("M"):
            kept.append(ch)
        else:
            kept.append(" ")
    return re.sub(r"\s+", " ", "".join(kept)).strip()


def parse_section(text: str | None) -> str | None:
    """Return a canonical section id such as '87' or '89(1)' from receipt text, or None."""
    if not text:
        return None
    text = text.translate(_BN_DIGITS)
    m = _SECTION.search(text) or _BARE_SECTION.match(text)
    if not m:
        return None
    return f"{m.group(1)}({m.group(2)})" if m.group(2) else m.group(1)


def contains(text: str, term: str) -> bool:
    """Whether `term` occurs in already-normalised `text`.

    Long ASCII terms match as substrings (stems like 'overload' also catch 'overloaded'). Short ASCII terms and all
    Bangla terms must start at a word boundary, so 'rash' matches 'rash driving' but not 'crash', and the Bangla
    word for 'permanent' (স্থায়ী) does not match inside the word for 'temporary' (অস্থায়ী).
    """
    term = normalize(term)
    if not term:
        return False
    if term.isascii():
        if len(term) >= 6:
            return term in text
        return re.search(r"(?<![a-z0-9])" + re.escape(term), text) is not None
    return re.search(r"(?<!\S)" + re.escape(term), text) is not None
