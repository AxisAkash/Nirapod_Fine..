"""Talking to the blockchain. Only hashes are ever sent: no name, receipt, amount or any readable case detail.

`get_chain()` returns a ready client, None when blockchain auditing is switched off, or raises ChainError when it is
switched on but the node or the contract cannot be reached. Tests replace `get_chain` with an in-memory chain.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from web3 import Web3
from web3.exceptions import ContractLogicError

from app.core.config import get_settings

ARTIFACT = Path(__file__).resolve().parents[1] / "chain" / "AuditRegistry.json"
# Hardhat's published development key for account #0. It is public, so it is only ever used against a local node.
HARDHAT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_RETRY_AFTER_S = 10.0
_unreachable_until = 0.0


class ChainError(Exception):
    """code: disabled | unreachable | not_deployed | no_write_access | tx_failed"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class Anchor:
    exists: bool
    source_hash: str
    content_hash: str
    timestamp: int
    rule_count: int


@dataclass
class OnChainCase:
    case_hash: str
    dataset_hash: str
    result_hash: str
    timestamp: int


@dataclass
class TxInfo:
    tx_hash: str
    block_number: int
    record_id: int | None = None


def _is_revert(e: Exception) -> bool:
    """A contract call that was refused. A real node and the in-memory test chain report this with different classes."""
    return isinstance(e, ContractLogicError) or type(e).__name__ == "TransactionFailed" or "revert" in str(e).lower()


def _b32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)


def _hex(b: bytes) -> str:
    return b.hex()


class ChainClient:
    def __init__(self, w3: Web3, address: str, private_key: str | None = None, unlocked_account: str | None = None, network_name: str = "Hardhat local"):
        art = json.loads(ARTIFACT.read_text())
        self.w3 = w3
        self.contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=art["abi"])
        self._key = private_key
        self._from = w3.eth.account.from_key(private_key).address if private_key else unlocked_account
        self.chain_id = int(w3.eth.chain_id)
        self.network = f"{network_name} (chain {self.chain_id})"

    @property
    def address(self) -> str:
        return self.contract.address

    def has_contract(self) -> bool:
        return len(self.w3.eth.get_code(self.contract.address)) > 0

    # ---- writing
    def _send(self, call) -> Any:
        try:
            if self._key:
                tx = call.build_transaction({"from": self._from, "nonce": self.w3.eth.get_transaction_count(self._from, "pending"),
                                             "chainId": self.chain_id})
                tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.25) + 20_000
                raw = self.w3.eth.account.sign_transaction(tx, self._key).raw_transaction
                tx_hash = self.w3.eth.send_raw_transaction(raw)
            else:
                tx_hash = call.transact({"from": self._from, "gas": 8_000_000})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        except Exception as e:
            if _is_revert(e):
                if "NotOwner" in str(e):
                    raise ChainError("no_write_access", "The backend's account is not allowed to write to the audit contract.") from None
                raise ChainError("tx_failed", "The blockchain refused the record.") from None
            raise ChainError("unreachable", "The blockchain could not be reached.") from e  # connection reset, timeout, nonce race
        if receipt["status"] != 1:
            raise ChainError("tx_failed", "The blockchain transaction failed.")
        return receipt

    def anchor_dataset(self, version_key: str, source_hash: str, content_hash: str, labels: list[str], leaves: list[str]) -> TxInfo:
        receipt = self._send(self.contract.functions.anchorDataset(_b32(version_key), _b32(source_hash), _b32(content_hash),
                                                                    [_b32(x) for x in labels], [_b32(x) for x in leaves]))
        return TxInfo("0x" + receipt["transactionHash"].hex().removeprefix("0x"), receipt["blockNumber"])

    def record_case(self, case_hash: str, dataset_hash: str, result_hash: str) -> TxInfo:
        receipt = self._send(self.contract.functions.recordCase(_b32(case_hash), _b32(dataset_hash), _b32(result_hash)))
        events = self.contract.events.CaseRecorded().process_receipt(receipt)
        record_id = int(events[0]["args"]["id"]) if events else None
        return TxInfo("0x" + receipt["transactionHash"].hex().removeprefix("0x"), receipt["blockNumber"], record_id)

    # ---- reading
    def get_dataset(self, version_key: str) -> Anchor | None:
        try:
            (source, content, ts, exists), count = self.contract.functions.getDataset(_b32(version_key)).call()  # struct field order
        except Exception as e:
            raise ChainError("unreachable", "The blockchain could not be read.") from e
        return Anchor(exists, _hex(source), _hex(content), int(ts), int(count)) if exists else None

    def get_rules(self, version_key: str) -> dict[str, str]:
        try:
            labels, leaves = self.contract.functions.getRules(_b32(version_key)).call()
        except Exception as e:
            raise ChainError("unreachable", "The blockchain could not be read.") from e
        return {_hex(lh): _hex(leaf) for lh, leaf in zip(labels, leaves, strict=True)}

    def get_case(self, record_id: int) -> OnChainCase | None:
        try:
            case_hash, dataset_hash, result_hash, ts = self.contract.functions.getCase(record_id).call()
        except Exception as e:
            if _is_revert(e):
                return None  # NoSuchRecord: the record is not on this chain
            raise ChainError("unreachable", "The blockchain could not be read.") from e
        return OnChainCase(_hex(case_hash), _hex(dataset_hash), _hex(result_hash), int(ts))


def _contract_address() -> str:
    settings = get_settings()
    if settings.blockchain_contract_address:
        return settings.blockchain_contract_address
    try:
        return json.loads(Path(settings.blockchain_deployment_file).read_text())["address"]
    except (OSError, ValueError, KeyError):
        raise ChainError("not_deployed", "The audit contract has not been deployed. Run `npm run deploy` in contracts/.") from None


def get_chain() -> ChainClient | None:
    global _unreachable_until
    settings = get_settings()
    if not settings.blockchain_enabled:
        return None
    if time.monotonic() < _unreachable_until:  # do not make every request wait on a node that is known to be down
        raise ChainError("unreachable", "The blockchain could not be reached.")
    w3 = Web3(Web3.HTTPProvider(settings.blockchain_rpc_url, request_kwargs={"timeout": 5}))
    try:
        if not w3.is_connected():
            raise ConnectionError
    except Exception:
        _unreachable_until = time.monotonic() + _RETRY_AFTER_S
        raise ChainError("unreachable", "The blockchain could not be reached.") from None
    host = urlparse(settings.blockchain_rpc_url).hostname or ""
    key = settings.blockchain_private_key or (HARDHAT_DEV_KEY if host in {"127.0.0.1", "localhost"} and settings.environment != "production" else None)
    if key is None:
        raise ChainError("no_write_access", "No blockchain account is configured (BLOCKCHAIN_PRIVATE_KEY).")
    client = ChainClient(w3, _contract_address(), private_key=key, network_name=settings.blockchain_network_name)
    if not client.has_contract():
        raise ChainError("not_deployed", "The audit contract was not found on this blockchain. It may have been reset.")
    return client
