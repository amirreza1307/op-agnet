"""Platform runtime configuration accessor.

Was previously a single-method class (``PlatformConfigService``) that wrapped
one staticmethod-like accessor. Replaced with a plain module-level function;
the legacy class name remains as a thin compat shim that forwards to the
function so existing imports keep compiling without controller edits.
"""
from __future__ import annotations

from typing import Any

from setup.config import config


def get_default_runtime_config() -> dict[str, Any]:
    return {
        "default_model_id": config.AGNO_MODEL,
        "default_model_provider": "openrouter",
        "default_base_url": config.OPENROUTER_BASE_URL,
        "default_session_table": config.PLATFORM_DEFAULT_SESSION_TABLE,
    }


class PlatformConfigService:
    @staticmethod
    def get_default_runtime_config() -> dict[str, Any]:
        return get_default_runtime_config()