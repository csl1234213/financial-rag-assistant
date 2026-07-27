import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

DEVELOPMENT_SECRET_KEY = "dev-secret-key-change-in-development"
_INSECURE_PRODUCTION_SECRETS = {
    "",
    DEVELOPMENT_SECRET_KEY,
    "dev-secret-key-change-in-production",
    "change-me-to-a-random-secret-key",
    "change-me",
    "your-secret-key",
}


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def _resolve_secret_key() -> str:
    """Return the configured signing key without allowing a production fallback.

    ``SECRET_KEY`` remains a backwards-compatible alias while deployments move to
    the explicit ``AUTH_SECRET_KEY`` name.  Development and test environments
    can still run without a secret-manager value; production cannot.
    """

    secret_key = (os.getenv("AUTH_SECRET_KEY") or os.getenv("SECRET_KEY") or "").strip()
    if _is_production() and secret_key in _INSECURE_PRODUCTION_SECRETS:
        raise RuntimeError(
            "AUTH_SECRET_KEY must be set to a non-placeholder value when APP_ENV=production."
        )

    return secret_key or DEVELOPMENT_SECRET_KEY


SECRET_KEY = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "1440"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
