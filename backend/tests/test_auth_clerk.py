"""Clerk token verification with a locally generated RSA key (no network, no real Clerk account)."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.core import security
from app.core.config import Settings, get_settings
from app.main import app

ISSUER = "https://clerk.example.test"


def _keypair(kid):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private.public_key(), as_dict=True) | {"kid": kid, "use": "sig", "alg": "RS256"}
    return private, jwk


KEY, JWK = _keypair("test-key-1")
OTHER_KEY, _ = _keypair("test-key-1")  # same kid, different key: a forged signature


def token(private=KEY, kid="test-key-1", **claims):
    now = int(time.time())
    payload = {"sub": "user_abc", "iss": ISSUER, "iat": now, "exp": now + 300} | claims
    return jwt.encode(payload, private, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def clerk(client, monkeypatch):
    settings = Settings(auth_mode="clerk", clerk_issuer=ISSUER, admin_emails=["boss@example.test"], _env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    calls = []
    monkeypatch.setattr(security, "fetch_jwks", lambda url: calls.append(url) or [JWK])
    security._jwks_cache.update(at=0.0, url=None, keys=[])
    yield calls
    app.dependency_overrides.pop(get_settings, None)


def get_me(client, tok):
    return client.get("/api/me", headers={"Authorization": f"Bearer {tok}"})


def test_valid_token_creates_the_user(client, clerk):
    r = get_me(client, token(email="a@example.test", name="Aisha Rahman"))
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.test" and r.json()["full_name"] == "Aisha Rahman" and r.json()["role"] == "user"


def test_signing_keys_are_fetched_from_the_issuer_and_cached(client, clerk):
    get_me(client, token())
    get_me(client, token())
    assert clerk == [f"{ISSUER}/.well-known/jwks.json"]


def test_admin_role_from_public_metadata(client, clerk):
    assert get_me(client, token(public_metadata={"role": "admin"})).json()["role"] == "admin"


def test_admin_role_from_the_admin_email_list(client, clerk):
    assert get_me(client, token(sub="user_boss", email="Boss@Example.test")).json()["role"] == "admin"


def test_role_is_updated_when_it_is_removed(client, clerk):
    assert get_me(client, token(public_metadata={"role": "admin"})).json()["role"] == "admin"
    assert get_me(client, token()).json()["role"] == "user"


def test_expired_token_is_rejected(client, clerk):
    assert get_me(client, token(exp=int(time.time()) - 3600)).status_code == 401


def test_wrong_issuer_is_rejected(client, clerk):
    assert get_me(client, token(iss="https://evil.example.test")).status_code == 401


def test_token_signed_with_another_key_is_rejected(client, clerk):
    assert get_me(client, token(private=OTHER_KEY)).status_code == 401


def test_token_without_subject_is_rejected(client, clerk):
    now = int(time.time())
    tok = jwt.encode({"iss": ISSUER, "exp": now + 300}, KEY, algorithm="RS256", headers={"kid": "test-key-1"})
    assert get_me(client, tok).status_code == 401


def test_unknown_key_id_is_rejected_after_one_refetch(client, clerk):
    assert get_me(client, token(kid="rotated-away")).status_code == 401
    assert len(clerk) == 2  # first fetch, then one refetch in case the key had rotated


def test_dev_tokens_do_not_work_in_clerk_mode(client, clerk):
    assert get_me(client, "dev-admin").status_code == 401


def test_audience_is_enforced_when_configured(client, monkeypatch):
    settings = Settings(auth_mode="clerk", clerk_issuer=ISSUER, clerk_audience="nirapod-api", _env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(security, "fetch_jwks", lambda url: [JWK])
    security._jwks_cache.update(at=0.0, url=None, keys=[])
    try:
        assert get_me(client, token(aud="nirapod-api")).status_code == 200
        assert get_me(client, token(aud="someone-else")).status_code == 401
        assert get_me(client, token()).status_code == 401
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_dev_mode_is_refused_in_production():
    with pytest.raises(ValueError, match="not allowed"):
        Settings(environment="production", auth_mode="dev", _env_file=None)


def test_clerk_mode_needs_an_issuer_or_jwks_url():
    with pytest.raises(ValueError, match="CLERK_ISSUER"):
        Settings(auth_mode="clerk", _env_file=None)


def test_admin_email_applies_to_existing_user_when_token_has_no_email(db, monkeypatch):
    """Session tokens carry no email, so the stored email must decide the admin role on later requests."""
    from app import models
    from app.core import security
    from app.core.config import Settings

    settings = Settings(_env_file=None, auth_mode="clerk", clerk_issuer="https://x.clerk.test", admin_emails=["boss@example.com"])
    user = models.User(clerk_user_id="user_x", email="boss@example.com", full_name=None, role="user")
    db.add(user)
    db.commit()
    monkeypatch.setattr(security, "_identity", lambda t, s: {"id": "user_x", "email": None, "name": None, "role": None})
    creds = type("C", (), {"scheme": "Bearer", "credentials": "t"})()
    assert security.get_current_user(creds, db, settings).role == "admin"
