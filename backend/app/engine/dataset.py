"""Build engine datasets from the seed data. A database loader can build the same Dataset from rows."""
from __future__ import annotations

from app.engine.models import Dataset, ExceptionRule, FineTier, Keyword, OffenceRule
from app.seed import data


def load_default_dataset() -> Dataset:
    rules = [
        OffenceRule(
            section=r["section"], title=r["title"], category=r["category"], min_fine=r["min_fine"],
            max_fine=r["max_fine"], fine_text=r["fine_text"], imprisonment_text=r["imprisonment_text"],
            repeat_rule_text=r["repeat_rule_text"], source_reference=r["source_reference"],
            aliases=[a["text"] for a in r["aliases"]],
            keywords=[Keyword(k["word"], k["weight"]) for k in r["keywords"]],
            matchable=r["matchable"],
            fine_tiers=[FineTier(t["label"], t["max_fine"], tuple(t["keywords"])) for t in r.get("fine_tiers", [])],
        )
        for r in data.OFFENCE_RULES
    ]
    exceptions = [
        ExceptionRule(
            key=x["key"], title=x["title"], category=x["category"], effect=x["effect"], section=x["section"],
            description=x["description"], vehicles=list(x["vehicles"]), conditions_text=list(x["conditions_text"]),
            scope_limit=x["scope_limit"], required_evidence=x["required_evidence"],
            source_reference=x["source_reference"],
            keywords=[Keyword(k["word"], k["weight"]) for k in x["keywords"]],
        )
        for x in data.EXCEPTION_RULES
    ]
    return Dataset(name=data.DATASET_NAME, rules=rules, exceptions=exceptions)
