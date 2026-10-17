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
