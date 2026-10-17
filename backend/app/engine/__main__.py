"""Command-line runner:  python -m app.engine "over speed" --amount 3000 --vehicle motorcycle"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime

from app.engine import PriorCase, ReceiptInput, explain, load_default_dataset, validate


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.engine", description="Validate a traffic fine receipt.")
    p.add_argument("reason", help="offence reason as written on the receipt")
    p.add_argument("--amount", type=int)
    p.add_argument("--section", help="section cited on the receipt, e.g. 87 or 89(1)")
    p.add_argument("--vehicle")
    p.add_argument("--notes", help="notes or a claimed exception")
    p.add_argument("--previous", action="append", default=[], metavar="SECTION:AMOUNT",
                   help="earlier fine by the same user, e.g. 87:3000 (repeatable)")
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    a = p.parse_args()

    history = []
    for i, item in enumerate(a.previous):
        section, amount = item.split(":")
        history.append(PriorCase(section, int(amount), datetime(2020, 1, 1 + i)))
    receipt = ReceiptInput(a.reason, a.amount, a.section, a.vehicle, a.notes)
    result = validate(receipt, load_default_dataset(), history)

    if a.json:
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False, default=lambda o: getattr(o, "value", str(o))))
        return
    rule = result.matched_rule
    print(f"Status      {result.status.value}")
    print(f"Section     {rule.section + ': ' + rule.title if rule else 'none'}")
    print(f"Confidence  {result.confidence}%")
    print(f"Charged     {a.amount if a.amount is not None else '-'}   Allowed {result.allowed_fine}   Max {result.max_fine}")
    if result.flags:
        print("Flags       " + ", ".join(result.flags))
    print("\nJustification")
    for j in result.justifications:
        print(f"  [{j.tone:4}] {j.title}\n         {j.text}")
    print(f"\nExplanation\n  {explain(result, receipt)}")


if __name__ == "__main__":
    main()
