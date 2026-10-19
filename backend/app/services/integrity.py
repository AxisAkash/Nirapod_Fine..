"""Fingerprints of the legal dataset, and the check that the rules in the database are the ones that were anchored.

Every column of a rule that a user can see, or that can change a verdict, is part of its fingerprint, so editing even
the displayed fine text is detected. The fingerprint of a whole version is a hash over its rules' fingerprints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.config import get_settings
from app.core.hashing import hash_object, sha256_text
from app.services import chain as chain_service
from app.services.chain import ChainClient, ChainError


# ---------- fingerprints ---------------------------------------------------------------------------------------
def label_hash(label: str) -> str:
    return sha256_text(label)


def version_key(version_id: Any) -> str:
    """The on-chain key of a dataset version: the SHA-256 of its id."""
    return sha256_text(str(version_id))


def offence_payload(r: models.OffenceRule) -> dict[str, Any]:
    return {
        "section": r.section_number, "title": r.offence_title, "description": r.offence_description,
        "category": r.offence_category, "min_fine": r.min_fine, "max_fine": r.max_fine, "fine_text": r.fine_text,
        "imprisonment_text": r.imprisonment_text, "penalty_points": r.penalty_points, "repeat_rule_text": r.repeat_rule_text,
        "source_reference": r.source_reference, "is_active": r.is_active, "matchable": r.matchable,
        "fine_tiers": r.fine_tiers or [],
        "aliases": sorted([a.alias_text, a.language] for a in r.aliases),
        "keywords": sorted([k.keyword, k.weight] for k in r.keywords),
    }


def exception_payload(x: models.ExceptionRule) -> dict[str, Any]:
    return {
        "key": x.rule_key, "title": x.exception_title, "description": x.exception_description,
        "applies_to_section": x.applies_to_section, "applies_to_category": x.applies_to_category,
        "conditions": x.conditions or {}, "scope_limit": x.scope_limit, "required_evidence": x.required_evidence,
        "source_reference": x.source_reference, "is_active": x.is_active,
        "keywords": sorted([k.keyword, k.weight] for k in x.keywords),
    }


def dataset_leaves(db: Session, version: models.DatasetVersion) -> dict[str, str]:
    """label -> fingerprint of that rule's complete content, e.g. {"offence:87": "ab12...", "exception:s30-emergency": ...}."""
    leaves: dict[str, str] = {}
    for r in db.scalars(
        select(models.OffenceRule).where(models.OffenceRule.dataset_version_id == version.id)
        .options(selectinload(models.OffenceRule.aliases), selectinload(models.OffenceRule.keywords))
    ):
        leaves[f"offence:{r.section_number}"] = hash_object(offence_payload(r))
    for x in db.scalars(
        select(models.ExceptionRule).where(models.ExceptionRule.dataset_version_id == version.id)
        .options(selectinload(models.ExceptionRule.keywords))
    ):
        leaves[f"exception:{x.rule_key}"] = hash_object(exception_payload(x))
    return leaves


def content_hash(leaves: dict[str, str]) -> str:
    return hash_object(leaves)


def describe(label: str) -> str:
    kind, _, name = label.partition(":")
    return f"Section {name}" if kind == "offence" else f"Exception {name}"


# ---------- checking the rules in the database against the anchor ---------------------------------------------
@dataclass
class DatasetCheck:
    status: str  # verified | tampered | unanchored | unchecked | disabled
    message: str
    changed: list[dict[str, str]] = field(default_factory=list)  # [{"what": "changed"|"added"|"removed", "name": "Section 87"}]
    content_hash: str | None = None
    anchored_hash: str | None = None
    anchor_tx: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "message": self.message, "changed": self.changed, "content_hash": self.content_hash,
                "anchored_hash": self.anchored_hash, "anchor_tx": self.anchor_tx}


# An anchor can never change once written, so what we read from the chain can be remembered for good.
_anchors: dict[str, tuple[chain_service.Anchor, dict[str, str]]] = {}


def forget_anchors() -> None:
    _anchors.clear()


def _known_labels(db: Session, leaves: dict[str, str]) -> dict[str, str]:
    """Labels we can recognise from a label fingerprint: the current ones, plus every section number in the law."""
    names = set(leaves) | {f"offence:{n}" for n in range(66, 106)} | {f"offence:{n}({i})" for n in (89, 92) for i in (1, 2)}
    names |= {f"exception:{k}" for (k,) in db.execute(select(models.ExceptionRule.rule_key).distinct())}
    from app.seed import data as seed  # the baseline rules: their names are public, so a removed one can still be named

    names |= {f"exception:{x['key']}" for x in seed.EXCEPTION_RULES}
    return {label_hash(n): n for n in names}


def _anchor_from_chain(version: models.DatasetVersion, chain: ChainClient) -> tuple[chain_service.Anchor, dict[str, str]] | None:
    key = version_key(version.id)
    if key in _anchors:
        return _anchors[key]
    anchor = chain.get_dataset(key)
    if anchor is None or not anchor.exists:
        return None
    _anchors[key] = (anchor, chain.get_rules(key))
    return _anchors[key]


def check_dataset(db: Session, version: models.DatasetVersion, chain: ChainClient | None = None) -> DatasetCheck:
    """Compare the rules now in the database with what was anchored on the chain when the version was activated."""
    if not get_settings().blockchain_enabled:
        return DatasetCheck("disabled", "Blockchain auditing is switched off.")
    leaves = dataset_leaves(db, version)
    now = content_hash(leaves)
    try:
        chain = chain or chain_service.get_chain()
        found = _anchor_from_chain(version, chain) if chain else None
    except ChainError:
        key = version_key(version.id)
        found = _anchors.get(key)
        if found is None:
            return DatasetCheck("unchecked", "The blockchain could not be reached, so the legal dataset could not be checked.", content_hash=now)
    if found is None:
        return DatasetCheck("unanchored", "This dataset version has not been recorded on the blockchain yet.", content_hash=now)
    anchor, rules = found
    if now == anchor.content_hash:
        return DatasetCheck("verified", "The legal dataset matches the version recorded on the blockchain.", content_hash=now,
                            anchored_hash=anchor.content_hash, anchor_tx=version.anchor_tx_hash)
    known = _known_labels(db, leaves)
    changed: list[dict[str, str]] = []
    current = {label_hash(lbl): (lbl, leaf) for lbl, leaf in leaves.items()}
    for lh, (lbl, leaf) in current.items():
        if lh not in rules:
            changed.append({"what": "added", "name": describe(lbl)})
        elif rules[lh] != leaf:
            changed.append({"what": "changed", "name": describe(lbl)})
    for lh in rules:
        if lh not in current:
            changed.append({"what": "removed", "name": describe(known[lh]) if lh in known else "a rule"})
    names = ", ".join(f"{c['name']} {c['what']}" for c in changed) or "the contents differ"
    return DatasetCheck("tampered", f"The legal dataset does not match the version recorded on the blockchain: {names}.", changed,
                        now, anchor.content_hash, version.anchor_tx_hash)


# ---------- anchoring a version ---------------------------------------------------------------------------------
def anchor_version(db: Session, version: models.DatasetVersion, chain: ChainClient | None = None) -> str:
    """Write the version's fingerprints to the chain. Returns "anchored", "pending" (chain unavailable) or "disabled".

    Safe to call again: a version that is already on the chain is checked, never written twice.
    """
    if not get_settings().blockchain_enabled:
        return "disabled"
    leaves = dataset_leaves(db, version)
    now = content_hash(leaves)
    try:
        chain = chain or chain_service.get_chain()
        if chain is None:
            return "disabled"
        key = version_key(version.id)
        existing = chain.get_dataset(key)
        if existing is not None and existing.exists:
            version.anchor_status = "anchored" if existing.content_hash == now else version.anchor_status
            version.anchored_content_hash = existing.content_hash
            return version.anchor_status or "pending"
        labels = sorted(leaves)
        tx = chain.anchor_dataset(key, version.source_hash, now, [label_hash(lbl) for lbl in labels], [leaves[lbl] for lbl in labels])
    except ChainError:
        version.anchor_status = "pending"
        return "pending"
    version.anchor_status = "anchored"
    version.anchor_tx_hash = tx.tx_hash
    version.anchor_block = tx.block_number
    version.anchored_content_hash = now
    version.anchored_at = _now()
    forget_anchors()
    return "anchored"


def _now():
    from app.models import utcnow

    return utcnow()


__all__ = ["DatasetCheck", "anchor_version", "check_dataset", "content_hash", "dataset_leaves", "forget_anchors", "version_key", "time"]
