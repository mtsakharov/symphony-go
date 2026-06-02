"""Hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError as PyJWTInvalidTokenError
from pydantic import ValidationError

from app.auth.exceptions import InvalidTokenError
from app.auth.schemas import TokenClaims
from app.core.config import get_settings

_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_DIGEST = "sha256"
_PBKDF2_ITERATIONS = 600_000
_PBKDF2_SALT_BYTES = 16


def hash_secret(secret: str) -> str:
    """Hash a password or shared secret."""

    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_DIGEST,
        secret.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    encoded_salt = salt.hex()
    encoded_digest = urlsafe_b64encode(digest).decode("ascii")
    return f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_secret(secret: str, secret_hash: str) -> bool:
    """Return whether a plaintext secret matches the stored hash."""

    try:
        algorithm, iteration_count, encoded_salt, expected_digest = secret_hash.split(
            "$", maxsplit=3
        )
        if algorithm != _PBKDF2_ALGORITHM:
            return False
        derived_digest = hashlib.pbkdf2_hmac(
            _PBKDF2_DIGEST,
            secret.encode("utf-8"),
            bytes.fromhex(encoded_salt),
            int(iteration_count),
        )
        actual_digest = urlsafe_b64encode(derived_digest).decode("ascii")
        return hmac.compare_digest(actual_digest, expected_digest)
    except ValueError:
        return False


def create_access_token(
    *,
    subject: str,
    subject_type: Literal["user", "device"],
    expires_in_seconds: int | None = None,
) -> tuple[str, int]:
    """Create a signed JWT for the supplied subject."""

    settings = get_settings()
    lifetime_seconds = expires_in_seconds or settings.jwt_access_token_expire_minutes * 60
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=lifetime_seconds)
    payload = {
        "sub": subject,
        "subject_type": subject_type,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, lifetime_seconds


def decode_access_token(token: str) -> TokenClaims:
    """Decode and validate a JWT."""

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims.model_validate(payload)
    except ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired") from exc
    except (PyJWTInvalidTokenError, ValidationError) as exc:
        raise InvalidTokenError("Token is invalid") from exc
