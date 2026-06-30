from __future__ import annotations

from typing import Any


class AuthenticatedPrincipal:
    __slots__ = ("principal_id", "subject", "claims", "auth_provider")

    def __init__(
        self,
        principal_id: str,
        subject: str | None = None,
        claims: dict[str, Any] | None = None,
        auth_provider: str | None = None,
    ):
        self.principal_id = principal_id
        self.subject = subject
        self.claims = claims or {}
        self.auth_provider = auth_provider

