"""Protocols isolating the rest of the platform from Agno-specific types (Phase 4)."""
from __future__ import annotations

from typing import Any, AsyncIterator, MutableMapping, Optional, Protocol, Union, runtime_checkable


@runtime_checkable
class RunResponseLike(Protocol):
    """The subset of an Agno ``RunResponse`` the platform actually reads."""

    content: Any
    session_id: Optional[str]
    status: Any
    tools: Any
    messages: Any

    def get_content_as_string(self) -> str: ...  # noqa: D401


@runtime_checkable
class AgentRuntime(Protocol):
    """The runtime surface the platform invokes — implemented by ``AgnoAgentRuntime``."""

    session_state: MutableMapping[str, Any]
    session_id: Optional[str]
    structured_outputs: Optional[bool]

    async def arun(
        self,
        *,
        input: str,  # noqa: A002 — Agno keyword
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_state: Optional[dict[str, Any]] = None,
        stream: bool = False,
        stream_events: Optional[bool] = None,
        output_schema: Any = None,
        yield_run_output: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[RunResponseLike, AsyncIterator[Any]]: ...
