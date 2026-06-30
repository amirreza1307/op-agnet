from __future__ import annotations

from secrets import compare_digest

from fastapi import Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.dependencies.models import AuthenticatedPrincipal
from api.errors import ServiceUnavailableError, UnauthorizedError
from services.platform.auth.agent_api_key_auth_service import AgentApiKeyAuthService
from services.platform.auth.models import AgentApiKeyPrincipal
from setup.config import config

_api_key_header = APIKeyHeader(
    name="X-Admin-Secret-Key",
    scheme_name="AdminSecretKey",
    auto_error=False,
)
_agent_api_key_header = APIKeyHeader(
    name="X-Agent-API-Key",
    scheme_name="AgentApiKey",
    auto_error=False,
)
_bearer_scheme = HTTPBearer(scheme_name="BearerToken", auto_error=False)

_FORWARDABLE_AUTH_HEADERS = (
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
)


def _extract_admin_secret(request: Request) -> str | None:
    configured_header_name = str(config.ADMIN_SECRET_HEADER_NAME or "").strip() or "X-Admin-Secret-Key"
    provided_secret = request.headers.get(configured_header_name)
    if provided_secret:
        return provided_secret.strip()

    authorization = str(request.headers.get("authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        bearer_value = authorization[7:].strip()
        if bearer_value:
            return bearer_value
    return None


async def require_admin_secret(
    request: Request,
    _api_key: str | None = Security(_api_key_header),
    _bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> None:
    configured_secret = str(config.ADMIN_SECRET_KEY or "").strip()
    if not configured_secret:
        raise ServiceUnavailableError("Admin secret key is not configured")

    provided_secret = _extract_admin_secret(request)
    if not provided_secret or not compare_digest(provided_secret, configured_secret):
        raise UnauthorizedError("Invalid admin secret key")


async def get_optional_principal(_request: Request) -> AuthenticatedPrincipal | None:
    return None


async def require_authenticated_principal(request: Request) -> AuthenticatedPrincipal:
    principal = await get_optional_principal(request)
    if principal is None:
        raise UnauthorizedError("Authentication is not configured")
    return principal


async def require_agent_api_key(
    api_key: str | None = Security(_agent_api_key_header),
) -> AgentApiKeyPrincipal:
    if not api_key:
        raise UnauthorizedError("Agent API key is required")
    return await AgentApiKeyAuthService.authenticate(api_key)


async def get_forwarded_auth_headers(request: Request) -> dict[str, str]:
    """Subset of incoming headers forwarded to downstream agent tools."""
    forwarded: dict[str, str] = {}
    for header_name in _FORWARDABLE_AUTH_HEADERS:
        value = request.headers.get(header_name)
        if value:
            forwarded[header_name] = value
    return forwarded

