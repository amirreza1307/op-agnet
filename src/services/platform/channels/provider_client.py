from __future__ import annotations

from typing import Any, Optional

import httpx

from api.errors import BadRequestError


class BotProviderClient:
    def __init__(self, *, token: str, api_base_url: str) -> None:
        self.token = token
        self.api_base_url = api_base_url.rstrip("/")

    def _method_url(self, method: str) -> str:
        return f"{self.api_base_url}/bot{self.token}/{method}"

    async def call(self, method: str, payload: Optional[dict[str, Any]] = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self._method_url(method), json=payload or {})
        except httpx.HTTPError as exc:
            raise BadRequestError(f"Bot API request failed: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise BadRequestError(
                f"Bot API returned non-JSON response (HTTP {response.status_code})"
            ) from exc

        if response.is_error or not body.get("ok", False):
            description = body.get("description") or f"HTTP {response.status_code}"
            raise BadRequestError(f"Bot API error: {description}", details=body)
        return body.get("result")

    async def get_me(self) -> dict[str, Any]:
        result = await self.call("getMe")
        return result if isinstance(result, dict) else {}

    async def set_webhook(
        self,
        *,
        url: str,
        secret_token: Optional[str] = None,
        drop_pending_updates: bool = False,
        allowed_updates: Optional[list[str]] = None,
    ) -> bool:
        payload: dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        if drop_pending_updates:
            payload["drop_pending_updates"] = True
        if allowed_updates is not None:
            payload["allowed_updates"] = allowed_updates
        return bool(await self.call("setWebhook", payload))

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> bool:
        payload = {"drop_pending_updates": True} if drop_pending_updates else {}
        return bool(await self.call("deleteWebhook", payload))

    async def get_webhook_info(self) -> dict[str, Any]:
        result = await self.call("getWebhookInfo")
        return result if isinstance(result, dict) else {}

    async def send_message(self, *, chat_id: int | str, text: str) -> dict[str, Any]:
        result = await self.call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
            },
        )
        return result if isinstance(result, dict) else {}

    async def send_chat_action(
        self, *, chat_id: int | str, action: str = "typing"
    ) -> None:
        await self.call("sendChatAction", {"chat_id": chat_id, "action": action})
