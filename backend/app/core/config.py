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

    # AI (OpenRouter). Without a key the app still works: details are typed in and explanations use the template.
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-5.6-luna"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_s: float = 90.0
    ai_explanations: bool = True  # let the model word the explanation (checked against the engine's output)
    ai_reads_per_hour: int = 20  # receipt reads per user per hour, so a loop cannot run up a bill
    ai_max_image_px: int = 2000  # longest side after shrinking an image before it is sent
    ai_max_pdf_pages: int = 3
    ai_read_passes: int = 2  # read each receipt this many times at once; fields that differ are flagged for checking
    # Blockchain audit. Only hashes are ever written. Off unless switched on and a node is running.
    blockchain_enabled: bool = False
    blockchain_rpc_url: str = "http://127.0.0.1:8545"
    blockchain_private_key: str | None = None  # the account that writes; the contract only accepts its deployer
    blockchain_contract_address: str | None = None  # defaults to the address in blockchain_deployment_file
    blockchain_deployment_file: Path = BACKEND_DIR.parent / "contracts" / "deployments" / "localhost.json"
    blockchain_network_name: str = "Hardhat local"

    @model_validator(mode="after")
    def _check(self) -> "Settings":
        if self.environment == "production" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev is not allowed when ENVIRONMENT=production")
        if self.auth_mode == "clerk" and not (self.clerk_issuer or self.clerk_jwks_url):
            raise ValueError("AUTH_MODE=clerk needs CLERK_ISSUER or CLERK_JWKS_URL")
        return self

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_api_key.strip())

    @property
    def jwks_url(self) -> str:
        return self.clerk_jwks_url or f"{(self.clerk_issuer or '').rstrip('/')}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
