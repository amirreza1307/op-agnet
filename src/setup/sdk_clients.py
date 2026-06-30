"""SDK client factories for non-Basalam services.

Basalam OpenAPI is accessed directly through ``basalam_sdk.BasalamClient``
— see :mod:`setup.basalam_client` for the user / app client factories.
This module is reserved for the remaining third-party SDKs that don't
have a corresponding piece in ``basalam-sdk``.
"""

from __future__ import annotations

from setup.config import config
from setup.sdks.numberland import (
    NumberlandOrder,
    NumberlandOrdersListResponse,
    NumberlandSDK,
    NumberlandSDKAuthException,
    NumberlandSDKException,
)

__all__ = [
    "NumberlandOrder",
    "NumberlandOrdersListResponse",
    "NumberlandSDK",
    "NumberlandSDKAuthException",
    "NumberlandSDKException",
]


def get_numberland_sdk() -> NumberlandSDK:
    """Build the shared Numberland admin SDK from client credentials config."""
    return NumberlandSDK(
        base_url=config.NUMBERLAND_ORDER_BASE_URL,
        auth_base_url=config.NUMBERLAND_AUTH_BASE_URL,
        client_id=config.NUMBERLAND_CLIENT_ID,
        client_secret=config.NUMBERLAND_CLIENT_SECRET,
        token_refresh_skew_seconds=config.NUMBERLAND_TOKEN_REFRESH_SKEW_SECONDS,
        timeout=config.NUMBERLAND_REQUEST_TIMEOUT_SECONDS,
    )
