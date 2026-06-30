"""Registry-backed listing of tool scripts for the admin panel.

Tools register themselves explicitly via ``@register_tool`` (see
:mod:`tools.registry`). This module exposes the registered tools — keyed by
their stable ``slug`` plus the Persian display name — instead of scanning the
filesystem. Moving or renaming a tool's file no longer changes its identity.
"""
from __future__ import annotations

from typing import Any

from tools.registry import list_registrations


class ScriptDiscovery:
    @staticmethod
    def list_tool_scripts() -> dict[str, Any]:
        return {"tools": list_registrations()}
