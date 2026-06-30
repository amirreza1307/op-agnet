from __future__ import annotations

import hashlib
import secrets

_KEY_MARKER = "agk"
_SECRET_BYTES = 32
_PREFIX_LENGTH = 12


def generate_agent_api_key() -> tuple[str, str, str]:
    secret = secrets.token_urlsafe(_SECRET_BYTES)
    api_key = f"{_KEY_MARKER}_{secret}"
    return api_key, secret[:_PREFIX_LENGTH], hash_agent_api_key(api_key)


def hash_agent_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
