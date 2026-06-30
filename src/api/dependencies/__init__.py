from api.dependencies.auth import (
    get_forwarded_auth_headers,
    get_optional_principal,
    require_agent_api_key,
    require_admin_secret,
    require_authenticated_principal,
)
from api.dependencies.models import AuthenticatedPrincipal
from services.platform.auth.models import AgentApiKeyPrincipal

__all__ = [
    "AgentApiKeyPrincipal",
    "AuthenticatedPrincipal",
    "get_forwarded_auth_headers",
    "get_optional_principal",
    "require_agent_api_key",
    "require_admin_secret",
    "require_authenticated_principal",
]

