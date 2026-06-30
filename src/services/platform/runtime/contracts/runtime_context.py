"""Typed runtime context (Phase 3 / F-02)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class RuntimeContext:
    """The canonical, typed identity for a single platform run."""

    vendor_id: Optional[int] = None
    principal_id: Optional[str] = None
    session_id: Optional[str] = None
    entry_node_id: Optional[int] = None
    entry_node_slug: Optional[str] = None
    forwarded_headers: Mapping[str, str] = field(default_factory=dict)

    def to_session_state(self) -> dict[str, Any]:
        """Render as a snake_case-only session_state dict."""
        state: dict[str, Any] = {}
        if self.vendor_id is not None:
            state["vendor_id"] = self.vendor_id
        if self.principal_id is not None:
            state["principal_id"] = self.principal_id
        if self.session_id is not None:
            state["current_session_id"] = self.session_id
        if self.entry_node_id is not None:
            state["entry_node_id"] = self.entry_node_id
        if self.entry_node_slug is not None:
            state["entry_node_slug"] = self.entry_node_slug
        if self.forwarded_headers:
            state["forwarded_auth_headers"] = dict(self.forwarded_headers)
        return state
