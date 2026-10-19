"""Score receipt reading against known answers.

Run:  python scripts/eval_extraction.py [receipts_dir] [--model openai/gpt-5.6-luna]
The folder needs a manifest.json: [{"file": "a.jpg", "expect": {"reason": ..., "amount": ..., ...}}].
Uses the real AI service (OPENROUTER_API_KEY from backend/.env) and prints accuracy per field and the cost per receipt.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.engine.normalize import normalize  # noqa: E402
from app.services.openrouter import AIError, OpenRouterClient  # noqa: E402
from app.services.receipt_reader import extract_from_file  # noqa: E402
from app.services.storage import sniff_type  # noqa: E402

TEXT_FIELDS = ["reason", "location", "vehicle", "receipt_number", "notes"]
ALL_FIELDS = ["reason", "amount", "date", "location", "vehicle", "receipt_number", "section", "notes"]


def same_text(expected: str, got: str | None) -> bool:
    if not got:
        return False
    e, g = normalize(expected), normalize(got)
    if e in g or g in e:
        return True
    words = [w for w in e.split() if len(w) >= 3]
    return bool(words) and sum(w in g for w in words) / len(words) >= 0.6


def judge(field: str, expected, got) -> str:
    """ok | wrong | missed (expected a value, got none) | spurious (expected none, got a value) | n/a"""
    if expected is None:
        return "ok" if got in (None, "") else "spurious"
    if got in (None, ""):
        return "missed"
    if field in TEXT_FIELDS:
        return "ok" if same_text(str(expected), str(got)) else "wrong"
    return "ok" if str(expected) == str(got) else "wrong"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder = Path(args[0]) if args else Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "receipts"
    settings = get_settings()
    if "--model" in sys.argv:
        settings.openrouter_model = sys.argv[sys.argv.index("--model") + 1]
    if not settings.ai_enabled:
        sys.exit("No OPENROUTER_API_KEY configured.")
    client = OpenRouterClient(settings)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf8"))

    tally = {f: {"ok": 0, "wrong": 0, "missed": 0, "spurious": 0} for f in ALL_FIELDS}
    cost = tokens_in = tokens_out = 0.0
    print(f"model: {settings.openrouter_model}   receipts: {len(manifest)}\n")
    for item in manifest:
        data = (folder / item["file"]).read_bytes()
        t0 = time.time()
        try:
            ex = extract_from_file(client, data, sniff_type(data) or "image/jpeg", settings)
        except AIError as e:
            print(f"{item['file']:<24} FAILED ({e.code}: {e})")
            continue
        secs = time.time() - t0
        u = ex.get("usage") or {}
        cost += float(u.get("cost") or 0)
        tokens_in += u.get("prompt_tokens", 0)
        tokens_out += u.get("completion_tokens", 0)
        flags = []
        exp = item["expect"]
        for f in ALL_FIELDS:
            got = ex["fields"][f]["value"]
            verdict = judge(f, exp.get(f), got)
            tally[f][verdict] += 1
            if verdict != "ok":
                flags.append(f"{f}:{verdict} (got {got!r})")
        if "legible" in exp and ex["legible"] != exp["legible"]:
            flags.append(f"legible should be {exp['legible']}")
        status = "all fields ok" if not flags else "; ".join(flags)
        unverified = [f for f, v in ex["fields"].items() if v["status"] == "unverified"]
        print(f"{item['file']:<24} {secs:4.1f}s  {status}" + (f"   [unverified: {', '.join(unverified)}]" if unverified else ""))

    print("\nper field          ok  wrong  missed  spurious")
    for f in ALL_FIELDS:
        t = tally[f]
        print(f"{f:<16} {t['ok']:>4} {t['wrong']:>6} {t['missed']:>7} {t['spurious']:>9}")
    total = sum(sum(t.values()) for t in tally.values())
    ok = sum(t["ok"] for t in tally.values())
    n = max(len(manifest), 1)
    print(f"\noverall: {ok}/{total} fields correct ({100 * ok / total:.0f}%)")
    print(f"tokens in/out: {int(tokens_in)}/{int(tokens_out)}   cost: ${cost:.4f} total, ${cost / n:.4f} per receipt")


if __name__ == "__main__":
    main()
