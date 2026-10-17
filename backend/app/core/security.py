"""Authentication: verify the caller and return the local user row.

AUTH_MODE=clerk verifies a Clerk session JWT against Clerk's public keys (RS256).
AUTH_MODE=dev accepts `Bearer dev-user`, `Bearer dev-admin` or `Bearer dev:<name>`; it is refused in production.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.core.config import Settings, get_settings
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)
_JWKS_TTL = 3600
_jwks_cache: dict[str, Any] = {"at": 0.0, "url": None, "keys": []}


def fetch_jwks(url: str) -> list[dict[str, Any]]:
    """Download Clerk's signing keys. Kept as a function so tests can replace it."""
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    return r.json()["keys"]


def _signing_key(token: str, settings: Settings) -> Any:
    kid = jwt.get_unverified_header(token).get("kid")
    url = settings.jwks_url
    now = time.time()
    for attempt in (0, 1):
        stale = _jwks_cache["url"] != url or now - _jwks_cache["at"] > _JWKS_TTL
        if stale or attempt == 1:  # second attempt: the key may have rotated, refetch once
            _jwks_cache.update(at=now, url=url, keys=fetch_jwks(url))
        for k in _jwks_cache["keys"]:
            if k.get("kid") == kid:
                return jwt.PyJWK(k).key
    raise jwt.InvalidTokenError("signing key not found")


def verify_clerk_token(token: str, settings: Settings) -> dict[str, Any]:
    key = _signing_key(token, settings)
    options = {"require": ["exp", "sub"], "verify_aud": bool(settings.clerk_audience)}
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer or None,
        audience=settings.clerk_audience or None,
        leeway=10,
        options=options,
    )


def _profile_from_clerk_api(clerk_user_id: str, settings: Settings) -> dict[str, Any]:
    """Optional: read email, name and role metadata when the session token does not carry them."""
    if not settings.clerk_secret_key:
        return {}
    try:
        r = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            timeout=10,
        )
        r.raise_for_status()
        u = r.json()
    except httpx.HTTPError:
        return {}
    primary = next((e for e in u.get("email_addresses", []) if e.get("id") == u.get("primary_email_address_id")), None)
    name = " ".join(p for p in [u.get("first_name"), u.get("last_name")] if p) or None
    return {"email": primary["email_address"] if primary else None, "name": name,
            "role": (u.get("public_metadata") or {}).get("role")}


def _unauthorised(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def _identity(token: str, settings: Settings) -> dict[str, Any]:
    if settings.auth_mode == "dev":
        if token == "dev-user":
            return {"id": "dev-user", "email": "dev-user@example.test", "name": "Dev User", "role": "user"}
        if token == "dev-admin":
            return {"id": "dev-admin", "email": "dev-admin@example.test", "name": "Dev Admin", "role": "admin"}
        if token.startswith("dev:") and len(token) > 4:
            name = token[4:]
            return {"id": f"dev:{name}", "email": f"{name}@example.test", "name": name, "role": "user"}
        raise _unauthorised("Invalid development token")
    try:
        claims = verify_clerk_token(token, settings)
    except (jwt.PyJWTError, httpx.HTTPError, KeyError):
        raise _unauthorised("Invalid or expired session token") from None
    meta = claims.get("public_metadata") or claims.get("metadata") or {}
    email = claims.get("email")
    name = claims.get("name") or " ".join(p for p in [claims.get("first_name"), claims.get("last_name")] if p) or None
    role = claims.get("role") or meta.get("role")
    return {"id": claims["sub"], "email": email, "name": name, "role": role, "needs_profile": not email}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> models.User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorised("Missing bearer token")
    ident = _identity(creds.credentials, settings)
    user = db.scalar(select(models.User).where(models.User.clerk_user_id == ident["id"]))
    if user is None and ident.get("needs_profile"):
        ident.update({k: v for k, v in _profile_from_clerk_api(ident["id"], settings).items() if v})
    email = ident.get("email")
    role = "admin" if (ident.get("role") == "admin" or (email and email.lower() in {e.lower() for e in settings.admin_emails})) else "user"
    if user is None:
        user = models.User(clerk_user_id=ident["id"], email=email, full_name=ident.get("name"), role=role)
        db.add(user)
    else:
        user.email = email or user.email
        user.full_name = ident.get("name") or user.full_name
        user.role = role
    db.commit()
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user
