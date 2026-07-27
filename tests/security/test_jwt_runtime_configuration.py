"""Focused tests for JWT secret key runtime configuration."""

import pytest

from auth import jwt


def _clear_auth_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("APP_ENV", "AUTH_SECRET_KEY", "SECRET_KEY"):
        monkeypatch.delenv(variable, raising=False)


def test_auth_secret_prefers_explicit_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "legacy-signing-key")
    monkeypatch.setenv("AUTH_SECRET_KEY", "explicit-signing-key")

    assert jwt._resolve_secret_key() == "explicit-signing-key"


def test_auth_secret_accepts_legacy_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "legacy-signing-key")

    assert jwt._resolve_secret_key() == "legacy-signing-key"


def test_auth_secret_rejects_missing_or_placeholder_production_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_auth_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        jwt._resolve_secret_key()

    monkeypatch.setenv("AUTH_SECRET_KEY", "change-me-to-a-random-secret-key")
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        jwt._resolve_secret_key()


def test_auth_secret_uses_development_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_environment(monkeypatch)

    assert jwt._resolve_secret_key() == jwt.DEVELOPMENT_SECRET_KEY
