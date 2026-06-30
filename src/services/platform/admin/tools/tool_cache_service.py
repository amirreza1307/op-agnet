"""Process-local cache of the active tools list."""

from __future__ import annotations

import asyncio
from time import monotonic

from database.models.main.tool import Tool
from database.repositories.main.tool_repo import ToolRepo
from setup.config import config


class ToolCacheService:
    _cache: tuple[Tool, ...] | None = None
    _expires_at: float = 0.0
    _lock = asyncio.Lock()

    @classmethod
    async def list_tools(cls) -> list[Tool]:
        now = monotonic()
        if cls._cache is not None and now < cls._expires_at:
            return list(cls._cache)

        async with cls._lock:
            now = monotonic()
            if cls._cache is not None and now < cls._expires_at:
                return list(cls._cache)

            tools = tuple(await ToolRepo.get_all_active_tools())
            cls._cache = tools
            cls._expires_at = now + max(0, config.CACHE_TOOLS_TTL_SECONDS)
            return list(tools)

    @classmethod
    async def invalidate_tools_cache(cls) -> None:
        async with cls._lock:
            cls._cache = None
            cls._expires_at = 0.0
