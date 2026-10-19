"""Recording a finished case on the blockchain, and checking it again later.

Three fingerprints go on the chain: the case (the confirmed receipt data plus a random salt), the dataset version that
was used, and the result. The salt stops anyone guessing a case's contents by hashing likely values. Nothing readable
is ever sent. Sealing never blocks or fails an analysis: if the chain is down the record stays "pending" and can be
retried.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.core.hashing import canonical_json, hash_object, sha256_text
from app.models import utcnow
from app.services import chain as chain_service
from app.services import integrity
from app.services.chain import ChainClient, ChainError

log = logging.getLogger("nirapod.sealing")


# ---------- the three fingerprints ---------------------------------------------------------------------------
def case_payload(case: models.MamlaCase) -> dict[str, Any]:
    return {
        "source": case.case_source, "dummy_url": case.dummy_url,
        "file": case.receipt.file_hash if case.receipt else None,
        "fields": {
            "reason": case.extracted_reason, "amount": case.extracted_amount,
            "date": case.extracted_date.isoformat() if case.extracted_date else None, "location": case.extracted_location,
            "vehicle": case.extracted_vehicle_type, "receipt_number": case.extracted_receipt_number,
            "section": case.extracted_section, "notes": case.claim_notes,
        },
    }


def result_payload(case: models.MamlaCase) -> dict[str, Any]:
    return {
        "status": case.validation_status, "summary": case.validation_summary, "explanation": case.ai_explanation,
        "confidence": float(case.confidence_score) if case.confidence_score is not None else None,
        "details": case.analysis_details,
    }


def salted_case_hash(case: models.MamlaCase, salt: str) -> str:
    return sha256_text(salt + canonical_json(case_payload(case)))


def current_hashes(db: Session, case: models.MamlaCase, salt: str) -> dict[str, str]:
    version = case.dataset_version
    dataset = integrity.content_hash(integrity.dataset_leaves(db, version)) if version else sha256_text("no-dataset")
    return {"case": salted_case_hash(case, salt), "dataset": dataset, "result": hash_object(result_payload(case))}


# ---------- recording ------------------------------------------------------------------------------------------
def latest_record(case: models.MamlaCase) -> models.BlockchainRecord | None:
    return case.records[-1] if case.records else None


def seal_case(db: Session, case: models.MamlaCase, chain: ChainClient | None = None) -> models.BlockchainRecord | None:
    """Record the case's current state. Returns the new record, or None when blockchain auditing is off."""
    if not get_settings().blockchain_enabled:
        return None
    salt = secrets.token_hex(16)
    hashes = current_hashes(db, case, salt)
    record = models.BlockchainRecord(
        mamla_case_id=case.id, case_hash=hashes["case"], dataset_hash=hashes["dataset"], result_hash=hashes["result"],
        salt=salt, status="pending", dataset_version_id=case.dataset_version_id,
    )
    db.add(record)
    db.flush()
    _send(db, case, record, chain)
    return record


def _send(db: Session, case: models.MamlaCase, record: models.BlockchainRecord, chain: ClientOrNone = None) -> None:
    try:
        chain = chain or chain_service.get_chain()
        if chain is None:
            record.status, record.error = "pending", "Blockchain auditing is switched off."
            return
        tx = chain.record_case(record.case_hash, record.dataset_hash, record.result_hash)
    except ChainError as e:
        record.status = "pending" if e.code in {"unreachable", "not_deployed"} else "failed"
        record.error = str(e)
    else:
        record.status, record.error = "sealed", None
        record.blockchain_network, record.smart_contract_address = chain.network, chain.address
        record.transaction_hash, record.block_number, record.chain_record_id = tx.tx_hash, tx.block_number, tx.record_id
        record.chain_id, record.sealed_at = chain.chain_id, utcnow()
    finally:
        case.blockchain_record_id = record.id
        db.flush()


ClientOrNone = ChainClient | None


def seal_quietly(db: Session, case: models.MamlaCase) -> None:
    """Seal after an analysis without ever letting a problem here fail the analysis."""
    try:
        seal_case(db, case)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("could not seal case %s", case.id)


def retry_record(db: Session, case: models.MamlaCase, chain: ChainClient | None = None) -> models.BlockchainRecord | None:
    """Try again to record a case whose record is pending or failed. If the case changed meanwhile, record the new state."""
    rec = latest_record(case)
    if rec is None or rec.status == "sealed":
        return rec
    if current_hashes(db, case, rec.salt or "") != {"case": rec.case_hash, "dataset": rec.dataset_hash, "result": rec.result_hash}:
        rec.status, rec.error = "failed", "The case changed before it could be recorded."
        return seal_case(db, case, chain)
    _send(db, case, rec, chain)
    return rec


# ---------- verifying ------------------------------------------------------------------------------------------------
def _row(label: str, now: str, recorded: str, onchain: str | None, anchored: str | None = None) -> dict[str, Any]:
    ok = now == recorded and (onchain is None or now == onchain) and (anchored is None or now == anchored)
    return {"item": label, "recomputed": now, "recorded": recorded, "on_chain": onchain, "ok": ok}


def history(case: models.MamlaCase) -> list[dict[str, Any]]:
    return [
        {"id": str(r.id), "status": r.status, "network": r.blockchain_network, "transaction_hash": r.transaction_hash,
         "block_number": r.block_number, "chain_record_id": r.chain_record_id, "created_at": r.created_at.isoformat(),
         "sealed_at": r.sealed_at.isoformat() if r.sealed_at else None, "error": r.error,
         "case_hash": r.case_hash, "dataset_hash": r.dataset_hash, "result_hash": r.result_hash,
         "current": r is case.records[-1]}
        for r in case.records
    ]


def verify_case(db: Session, case: models.MamlaCase, chain: ChainClient | None = None) -> dict[str, Any]:
    """Recompute everything from the database and compare it with the record and with the chain."""
    base = {"history": history(case), "rows": [], "dataset_check": None}
    rec = latest_record(case)
    if rec is None:
        return {**base, "status": "not_recorded", "message": "This case has not been recorded on the blockchain."}
    if rec.status != "sealed":
        why = "waiting to be recorded" if rec.status == "pending" else "could not be recorded"
        return {**base, "status": rec.status, "message": f"The record for this case is {why}. {rec.error or ''}".strip()}

    now = current_hashes(db, case, rec.salt or "")
    chain_problem: str | None = None
    on_chain = None
    anchor_hash: str | None = None
    version = case.dataset_version
    try:
        chain = chain or chain_service.get_chain()
        if chain is None:
            chain_problem = "Blockchain auditing is switched off."
        else:
            if rec.chain_record_id is not None:
                on_chain = chain.get_case(rec.chain_record_id)
            anchor = chain.get_dataset(integrity.version_key(version.id)) if version else None
            anchor_hash = anchor.content_hash if anchor else None
    except ChainError as e:
        if e.code == "not_deployed":  # the contract is not on this chain at all: it was reset or replaced
            chain, on_chain, chain_problem = None, None, None
            return {**base, "status": "not_on_chain", "rows": [
                _row("Case", now["case"], rec.case_hash, None), _row("Dataset", now["dataset"], rec.dataset_hash, None),
                _row("Result", now["result"], rec.result_hash, None)],
                "message": "The record was not found on the blockchain. The chain may have been reset or replaced."}
        chain_problem = str(e)

    if chain_problem is None and on_chain is None:
        return {**base, "status": "not_on_chain", "rows": [
            _row("Case", now["case"], rec.case_hash, None), _row("Dataset", now["dataset"], rec.dataset_hash, None),
            _row("Result", now["result"], rec.result_hash, None)],
            "message": "The record was not found on the blockchain. The chain may have been reset or replaced."}

    rows = [
        _row("Case", now["case"], rec.case_hash, on_chain.case_hash if on_chain else None),
        _row("Dataset", now["dataset"], rec.dataset_hash, on_chain.dataset_hash if on_chain else None, anchor_hash),
        _row("Result", now["result"], rec.result_hash, on_chain.result_hash if on_chain else None),
    ]
    dataset_check = integrity.check_dataset(db, version, chain).as_dict() if version and chain else None
    if chain_problem:
        return {**base, "rows": rows, "status": "unavailable", "dataset_check": dataset_check,
                "message": f"{chain_problem} Only the stored values could be compared, not the blockchain."}
    bad = [r["item"] for r in rows if not r["ok"]]
    if not bad:
        return {**base, "rows": rows, "status": "verified", "dataset_check": dataset_check,
                "message": "The case, the legal dataset and the result are unchanged since they were recorded on the blockchain."}
    meaning = {"Case": "the case data was changed", "Dataset": "the legal dataset was changed", "Result": "the result or its explanation was changed"}
    detail = "; ".join(meaning[b] for b in bad)
    if "Dataset" in bad and dataset_check and dataset_check.get("changed"):
        detail += f" ({dataset_check['message'].split(': ', 1)[-1].rstrip('.')})"
    return {**base, "rows": rows, "status": "mismatch", "dataset_check": dataset_check,
            "message": f"Verification failed: {detail} after it was recorded."}
