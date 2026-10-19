"""API tests run against a real PostgreSQL database (`nirapod_test` from docker-compose)."""

import os
import tempfile
from pathlib import Path

# Must be set before any `app` module is imported: the engine and settings read these once.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://nirapod:nirapod@localhost:5432/nirapod_test"
)
os.environ["AUTH_MODE"] = "dev"
os.environ["ENVIRONMENT"] = "test"
# Tests must never reach the real AI service, whatever backend/.env contains. They inject a fake client instead.
os.environ["OPENROUTER_API_KEY"] = ""
# Likewise for the blockchain: tests use an in-memory chain through the `chain` fixture, never a real node.
os.environ["BLOCKCHAIN_ENABLED"] = "false"
_STORAGE = tempfile.mkdtemp(prefix="nirapod-test-storage-")
os.environ["STORAGE_DIR"] = _STORAGE

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.datasets import seed_default_dataset  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
TABLES = (
    "blockchain_records, mamla_history, mamla_exception_checks, mamla_case_matches, mamla_cases, uploaded_receipts, "
    "exception_keywords, exception_rules, offence_keywords, offence_aliases, offence_rules, dataset_versions, users"
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture(scope="session", autouse=True)
def _migrated():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_db(_migrated):
    """Every test starts from an empty database with the seeded dataset."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        seed_default_dataset(db)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def auth(token: str = "dev-user") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_h():
    return auth("dev-user")


@pytest.fixture
def admin_h():
    return auth("dev-admin")


@pytest.fixture
def other_h():
    return auth("dev:someone-else")


# ---------------------------------------------------------------- an in-memory blockchain for the audit tests
import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402


@pytest.fixture
def chain(monkeypatch):
    """A real AuditRegistry contract on an in-memory test chain, with blockchain auditing switched on."""
    from web3 import EthereumTesterProvider, Web3

    from app.core.config import get_settings
    from app.services import chain as cs
    from app.services import integrity

    monkeypatch.setattr(get_settings(), "blockchain_enabled", True)
    integrity.forget_anchors()
    art = json.loads(cs.ARTIFACT.read_text())
    holder = SimpleNamespace(down=False, client=None, gone=False)

    def deploy():
        w3 = holder.w3 if hasattr(holder, "w3") else Web3(EthereumTesterProvider())
        acct = w3.eth.accounts[0]
        tx = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"]).constructor().transact({"from": acct, "gas": 3_000_000})
        address = w3.eth.wait_for_transaction_receipt(tx).contractAddress
        holder.w3, holder.client, holder.gone = w3, cs.ChainClient(w3, address, unlocked_account=acct), False

    def get_chain():
        if holder.down:
            raise cs.ChainError("unreachable", "The blockchain could not be reached.")
        if holder.gone:
            raise cs.ChainError("not_deployed", "The audit contract was not found on this blockchain. It may have been reset.")
        return holder.client

    holder.redeploy = deploy  # a fresh contract on the same chain: every earlier record is gone
    holder.wipe = lambda: setattr(holder, "gone", True)  # the whole chain was reset
    deploy()
    monkeypatch.setattr(cs, "get_chain", get_chain)
    yield holder
    integrity.forget_anchors()
