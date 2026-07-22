"""Authenticated encryption for credentials persisted in the database."""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


_PREFIX = "enc:v1:"


def _configured_keys() -> tuple[str, ...]:
    configured = os.environ.get("CREDENTIAL_ENCRYPTION_KEYS", "").strip()
    if configured:
        keys = tuple(part.strip() for part in configured.split(",") if part.strip())
    else:
        single = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "").strip()
        keys = (single,) if single else ()
    return keys


@lru_cache(maxsize=8)
def _fernet_for_keys(keys: tuple[str, ...]) -> MultiFernet:
    if not keys:
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY is not configured")
    try:
        return MultiFernet([Fernet(key.encode("ascii")) for key in keys])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY is invalid") from exc


def validate_secret_store_configuration() -> None:
    _fernet_for_keys(_configured_keys())


def secret_store_configured() -> bool:
    return bool(_configured_keys())


def is_encrypted_secret(value: str | None) -> bool:
    return str(value or "").startswith(_PREFIX)


def encrypt_secret(value: str | None) -> str:
    plaintext = str(value or "")
    if not plaintext:
        return ""
    if is_encrypted_secret(plaintext):
        decrypt_secret(plaintext)
        return plaintext
    token = _fernet_for_keys(_configured_keys()).encrypt(plaintext.encode("utf-8"))
    return _PREFIX + token.decode("ascii")


def decrypt_secret(value: str | None) -> str:
    stored = str(value or "")
    if not stored:
        return ""
    if not is_encrypted_secret(stored):
        return stored
    try:
        plaintext = _fernet_for_keys(_configured_keys()).decrypt(
            stored[len(_PREFIX):].encode("ascii")
        )
    except (InvalidToken, UnicodeError) as exc:
        raise RuntimeError("Stored credential cannot be decrypted") from exc
    return plaintext.decode("utf-8")


def secret_needs_migration(value: str | None) -> bool:
    return bool(str(value or "")) and not is_encrypted_secret(value)
