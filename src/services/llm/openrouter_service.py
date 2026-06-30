from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from api.errors import ServiceUnavailableError
from database.repositories.main.llm_request_log_repo import LlmRequestLogRepo
from setup.config import config

log = logging.getLogger(__name__)


class OpenRouterService:
    def __init__(self) -> None:
        self.api_key = str(config.OPENROUTER_API_KEY or "").strip()
        self.base_url = str(config.OPENROUTER_BASE_URL or "").strip()
        self.timeout = config.OPENROUTER_TIMEOUT
        self.default_model = str(config.OPENROUTER_TOOL_MODEL or config.AGNO_MODEL or "").strip()
        self.proxy = str(config.OPENROUTER_PROXY or "").strip() or None

    async def run_prompt(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        scope: str = "unknown",
    ) -> str:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.run_messages(messages=messages, model=model, scope=scope)

    async def run_messages(
        self,
        *,
        messages: list[dict],
        model: Optional[str] = None,
        scope: str = "unknown",
    ) -> str:
        """Send a pre-built ``messages`` list to OpenRouter. Supports the
        OpenAI multimodal content shape (text + image_url blocks)."""
        if not self.api_key:
            raise ServiceUnavailableError("OpenRouter API key is not configured")

        http_client = httpx.AsyncClient(proxy=self.proxy) if self.proxy else None
        client_kwargs = {
            "api_key": self.api_key,
            "base_url": self.base_url or "https://openrouter.ai/api/v1",
            "timeout": self.timeout,
        }
        if http_client is not None:
            client_kwargs["http_client"] = http_client

        client = AsyncOpenAI(**client_kwargs)
        used_model = model or self.default_model or "openai/gpt-4o-mini"
        try:
            response = await client.chat.completions.create(
                model=used_model,
                messages=messages,
                temperature=0.5,
                extra_body={"usage": {"include": True}},
            )
            content = response.choices[0].message.content
            text = str(content or "").strip()
            await self._log_request(
                scope=scope,
                model=used_model,
                messages=messages,
                response_text=text,
                response=response,
            )
            return text
        finally:
            if http_client is not None:
                await http_client.aclose()

    async def _log_request(
        self,
        *,
        scope: str,
        model: str,
        messages: list[dict],
        response_text: str,
        response: Any,
    ) -> None:
        try:
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            cost_usd: Optional[float] = _extract_cost(response, usage)
            if cost_usd is None:
                log.debug(
                    "openrouter: cost missing in response (scope=%s model=%s)",
                    scope, model,
                )

            payload = {
                "scope": str(scope or "unknown")[:128],
                "model": model,
                "messages": json.dumps(_sanitize_messages(messages), ensure_ascii=False),
                "response": response_text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            }

            await LlmRequestLogRepo.create_return(payload)
        except Exception as exc:
            log.warning("openrouter: failed to persist request log err=%s", exc)


def _extract_cost(response: Any, usage: Any) -> Optional[float]:
    """Pull the OpenRouter cost from a chat-completions response.

    OpenRouter only returns ``cost`` when the request body includes
    ``usage: {include: true}``. The OpenAI SDK puts unknown fields on
    ``model_extra``; older SDKs fall back to attribute access. The cost may
    live on either the top-level response or the nested usage object.
    """
    candidates: list[Any] = []
    for obj in (usage, response):
        if obj is None:
            continue
        extra = getattr(obj, "model_extra", None)
        if isinstance(extra, dict):
            candidates.append(extra.get("cost"))
            inner_usage = extra.get("usage")
            if isinstance(inner_usage, dict):
                candidates.append(inner_usage.get("cost"))
        candidates.append(getattr(obj, "cost", None))

    for value in candidates:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    """Truncate large image data URIs from logged messages so the JSON stays
    readable. Keeps text content untouched."""
    sanitized: list[dict] = []
    for msg in messages:
        if not isinstance(msg, dict):
            sanitized.append({"role": "unknown", "content": str(msg)})
            continue
        content = msg.get("content")
        if isinstance(content, list):
            new_parts: list[Any] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url_val = ""
                    if isinstance(part.get("image_url"), dict):
                        url_val = str(part["image_url"].get("url") or "")
                    elif isinstance(part.get("image_url"), str):
                        url_val = part["image_url"]
                    if url_val.startswith("data:"):
                        new_parts.append({"type": "image_url", "image_url": {"url": "<data-uri-omitted>"}})
                    else:
                        new_parts.append(part)
                else:
                    new_parts.append(part)
            sanitized.append({"role": msg.get("role"), "content": new_parts})
        else:
            sanitized.append({"role": msg.get("role"), "content": content})
    return sanitized


openrouter_service = OpenRouterService()
