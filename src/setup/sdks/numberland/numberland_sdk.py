"""Numberland SDK - admin order-service integration.

Wraps the Numberland admin orders API. Authentication is service-to-service:
the SDK obtains a client-credentials access token and sends it as a bearer token
on every API call.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from setup.sdks.base_sdk import (
    BaseSDK,
    SDKException,
    SDKResponseException,
    timeout_guard,
    with_auth_token,
    with_retry,
)
from setup.sdks.numberland.output_schemas import (
    NumberlandOrder,
    NumberlandOrdersListResponse,
)


class NumberlandSDKException(SDKResponseException):
    """Raised when the Numberland service returns an unexpected response."""

    def __str__(self) -> str:
        return f"Numberland SDK Error (Status {self.status_code}): {self.response.text}"


class NumberlandSDKAuthException(SDKException):
    """Raised when Numberland client-credentials auth fails."""


class _NumberlandAuthService:
    """Numberland client-credentials auth adapter."""

    def __init__(
        self,
        *,
        auth_base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._auth_base_url = auth_base_url.rstrip("/")
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self.last_error = ""

    async def get_client_token(self) -> dict[str, Any] | None:
        response = await self._http_client.post(
            f"{self._auth_base_url}/token",
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        )
        if response.status_code == 200:
            self.last_error = ""
            return response.json()
        self.last_error = f"HTTP {response.status_code}: {_response_error_message(response)}"
        return None

    def has_access(self, token: str, permissions: list[str]) -> bool:
        raise NotImplementedError

    def verify_token(self, token: str) -> dict | None:
        raise NotImplementedError

    def is_client_token(
        self, token: str, allowed_clients: set[str] | None = None
    ) -> bool:
        raise NotImplementedError

    def client_has_access(
        self,
        token: str,
        perms: list[str],
        allowed_clients: set[str] | None = None,
    ) -> bool:
        raise NotImplementedError

    async def close(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()


class _NumberlandTokenProvider:
    """Caches client-credentials tokens and refreshes before expiry."""

    def __init__(
        self,
        auth_service: _NumberlandAuthService,
        *,
        refresh_skew_seconds: int,
    ):
        self._auth_service = auth_service
        self._refresh_skew_seconds = max(0, int(refresh_skew_seconds))
        self._lock = asyncio.Lock()
        self._access_token = ""
        self._expires_at = 0.0

    async def get_auth_header(self) -> str:
        token = await self.get_access_token()
        return f"Bearer {token}"

    async def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._expires_at - self._refresh_skew_seconds:
            return self._access_token

        async with self._lock:
            now = time.time()
            if self._access_token and now < self._expires_at - self._refresh_skew_seconds:
                return self._access_token

            token_data = await self._auth_service.get_client_token()
            if not token_data or not token_data.get("access_token"):
                suffix = (
                    f" ({self._auth_service.last_error})"
                    if self._auth_service.last_error
                    else ""
                )
                raise NumberlandSDKAuthException(
                    f"Numberland auth failed to return an access_token{suffix}",
                    error_type="auth_failed",
                )

            expires_in = int(token_data.get("expires_in", 15 * 60))
            self._access_token = str(token_data["access_token"])
            self._expires_at = now + max(1, expires_in)
            return self._access_token


class NumberlandSDK(BaseSDK):
    """SDK for the Numberland admin order service."""

    def __init__(
        self,
        base_url: str = "https://order.numberland.ir",
        auth_base_url: str = "https://auth.numberland.ir",
        client_id: str = "",
        client_secret: str = "",
        token_refresh_skew_seconds: int = 30,
        user_agent: str = "VendorAgent/1.0",
        timeout: float = 20.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(base_url, user_agent, timeout, http_client)
        self._http_client.headers["accept"] = "application/json"
        self._http_client.headers["accept-language"] = "fa-IR"
        self._http_client.headers["origin"] = "https://admin.nmbr.ir"
        self._http_client.headers["referer"] = "https://admin.nmbr.ir/"

        self._auth_service = _NumberlandAuthService(
            auth_base_url=auth_base_url,
            client_id=client_id,
            client_secret=client_secret,
            timeout=timeout,
        )
        self._token_provider = _NumberlandTokenProvider(
            self._auth_service,
            refresh_skew_seconds=token_refresh_skew_seconds,
        )

    async def _set_auth_token(self) -> None:
        self._http_client.headers["Authorization"] = (
            await self._token_provider.get_auth_header()
        )

    async def _set_secret_key(self) -> None:
        pass

    @with_retry()
    @timeout_guard
    @with_auth_token
    async def list_orders(
        self,
        *,
        sort: str = "created_at:desc",
        limit: int = 10,
        offset: int = 0,
    ) -> NumberlandOrdersListResponse:
        """``GET /v1/admin/orders`` - paginated admin order list."""
        response = await self._http_client.get(
            "/v1/admin/orders",
            params={"sort": sort, "limit": int(limit), "offset": int(offset)},
        )
        self._raise_for_status(response, "list orders")
        return _parse_orders_response(response.json(), limit=int(limit), offset=int(offset))

    async def close(self) -> None:
        await self._auth_service.close()
        await super().close()

    def _raise_for_status(self, response: httpx.Response, action: str) -> None:
        if response.status_code >= 400:
            raise NumberlandSDKException(
                f"Numberland service failed to {action}", response=response
            )


def _parse_orders_response(
    payload: Any,
    *,
    limit: int,
    offset: int,
) -> NumberlandOrdersListResponse:
    if isinstance(payload, list):
        return NumberlandOrdersListResponse(
            data=[NumberlandOrder.model_validate(item) for item in payload],
            limit=limit,
            offset=offset,
            raw=payload,
        )

    if not isinstance(payload, dict):
        return NumberlandOrdersListResponse(limit=limit, offset=offset, raw=payload)

    data = payload.get("data")
    if data is None:
        data = payload.get("items") or payload.get("orders") or []
    if not isinstance(data, list):
        data = []

    response_data: Dict[str, Any] = dict(payload)
    response_data["data"] = [NumberlandOrder.model_validate(item) for item in data]
    response_data.setdefault("limit", limit)
    response_data.setdefault("offset", offset)
    response_data["raw"] = payload
    return NumberlandOrdersListResponse.model_validate(response_data)


def _response_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(data, dict):
        message = data.get("message") or data.get("error") or data.get("detail")
        if message:
            return str(message)
    return str(data)[:200]
