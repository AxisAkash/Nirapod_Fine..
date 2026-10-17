"""Cross-check the seed data against the source PDF text.

Run:  python scripts/verify_seed.py
Needs `pdftotext` (poppler). Parses the section/fine table in the fines PDF and compares every section
number, minimum and maximum with app/seed/data.py. Exits non-zero on any difference.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.seed.data import OFFENCE_RULES, SOURCE_FILES  # noqa: E402

LAKH = 100_000
ROW = re.compile(r"^\s+(\d{2,3}(?:\(\d\))?)\s{2,}(.*)$")
RANGE = re.compile(r"৳\s*([\d,]+)\s*(lakh)?\s*[–-]\s*৳?\s*([\d,]+)\s*(lakh)?")
SINGLE = re.compile(r"৳\s*([\d,]+)\s*(lakh)?")


def to_taka(num: str, lakh: str | None) -> int:
    n = int(num.replace(",", ""))
    return n * LAKH if lakh else n


def parse_fine(text: str) -> tuple[int, int | None]:
    m = RANGE.search(text)
    if m:
        a, a_lakh, b, b_lakh = m.groups()
        if b_lakh and not a_lakh and int(a.replace(",", "")) < 100:
            a_lakh = b_lakh  # "1-5 lakh": the unit applies to both ends
        return to_taka(a, a_lakh), to_taka(b, b_lakh)
    amounts = [to_taka(n, l) for n, l in SINGLE.findall(text)]
    return (0, max(amounts)) if amounts else (0, None)


def main() -> int:
    pdf = ROOT / "data" / "source" / SOURCE_FILES[0]
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    lines = text.splitlines()
    fine_col = 90  # the fine column starts well to the right of the offence column in the PDF layout
    row_idx = {i: ROW.match(line).group(1) for i, line in enumerate(lines) if ROW.match(line)}

    def right_cell(line: str) -> str | None:
        chunk = re.split(r"\s{2,}", line.rstrip())[-1].strip()
        return chunk if chunk and line.rfind(chunk) >= fine_col else None

    # A fine cell can wrap onto the lines above and below its section line, so attach every right-column
    # fragment to the nearest section line.
    cells: dict[int, list[str]] = {i: [] for i in row_idx}
    for i, line in enumerate(lines):
        cell = right_cell(line)
        if cell is None or "Fine / penalty" in line:
            continue
        nearest = min(row_idx, key=lambda r: (abs(r - i), r))
        if abs(nearest - i) <= 2:
            cells[nearest].append((i, cell))
    parsed: dict[str, tuple[int, int | None]] = {}
    for i, section in row_idx.items():
        joined = " ".join(c for _, c in sorted(cells[i]))
        parsed[section] = parse_fine(joined)
    seeded = {r["section"]: (r["min_fine"], r["max_fine"]) for r in OFFENCE_RULES}

    problems = []
    for s in sorted(set(parsed) | set(seeded), key=lambda x: (int(re.match(r"\d+", x).group()), x)):
        if s not in parsed:
            problems.append(f"{s}: in seed but not found in PDF")
        elif s not in seeded:
            problems.append(f"{s}: in PDF but missing from seed")
        elif parsed[s] != seeded[s]:
            problems.append(f"{s}: PDF {parsed[s]} != seed {seeded[s]}")
    print(f"PDF sections parsed: {len(parsed)}   seeded rules: {len(seeded)}")
    for s in sorted(parsed, key=lambda x: (int(re.match(r"\d+", x).group()), x)):
        lo, hi = parsed[s]
        hi_text = "none" if hi is None else f"{hi:,}"
        print(f"  {s:>6}  min {lo:>7,}  max {hi_text:>9}")
    if problems:
        print("\nMISMATCHES:")
        print("\n".join("  " + p for p in problems))
        return 1
    print("\nOK: every section, minimum and maximum matches the PDF.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
