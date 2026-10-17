from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Nirapod Fine API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://nirapod:nirapod@localhost:5432/nirapod"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Authentication. "dev" accepts `Authorization: Bearer dev-user` / `dev-admin` and is refused in production.
    auth_mode: Literal["dev", "clerk"] = "dev"
    clerk_issuer: str | None = None  # e.g. https://your-app.clerk.accounts.dev
    clerk_jwks_url: str | None = None  # defaults to <issuer>/.well-known/jwks.json
    clerk_audience: str | None = None
    clerk_secret_key: str | None = None  # optional: lets the API read email and name from Clerk
    admin_emails: list[str] = []  # these users get the admin role regardless of Clerk metadata

    # Receipt files
    storage_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 10

    @model_validator(mode="after")
    def _check(self) -> "Settings":
        if self.environment == "production" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev is not allowed when ENVIRONMENT=production")
        if self.auth_mode == "clerk" and not (self.clerk_issuer or self.clerk_jwks_url):
            raise ValueError("AUTH_MODE=clerk needs CLERK_ISSUER or CLERK_JWKS_URL")
        return self

    @property
    def jwks_url(self) -> str:
        return self.clerk_jwks_url or f"{(self.clerk_issuer or '').rstrip('/')}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
