"""Adapter wrapping Agno's ``Agent`` behind the :class:`AgentRuntime` Protocol (Phase 4)."""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional, Union

from agno.agent import Agent

from services.platform.runtime.contracts.agent_runtime import (
    AgentRuntime,
    RunResponseLike,
)


class AgnoAgentRuntime:
    """Thin façade isolating the rest of the platform from Agno's API surface.

    All Agno-specific calls live here; new application code should depend on
    the :class:`AgentRuntime` Protocol from ``contracts.agent_runtime``
    rather than importing ``agno.agent`` directly.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    @property
    def session_state(self):
        return self._agent.session_state

    @session_state.setter
    def session_state(self, value: Any) -> None:
        self._agent.session_state = value

    @property
    def session_id(self) -> Optional[str]:
        return getattr(self._agent, "session_id", None)

    @property
    def structured_outputs(self) -> Optional[bool]:
        return getattr(self._agent, "structured_outputs", None)

    @structured_outputs.setter
    def structured_outputs(self, value: Optional[bool]) -> None:
        self._agent.structured_outputs = value

    @property
    def add_history_to_context(self) -> Optional[bool]:
        return getattr(self._agent, "add_history_to_context", None)

    @property
    def num_history_runs(self) -> Optional[int]:
        return getattr(self._agent, "num_history_runs", None)

    @property
    def raw(self) -> Agent:
        """Escape hatch for code that genuinely needs the underlying Agno Agent."""
        return self._agent

    async def arun(self, **kwargs: Any) -> Union[RunResponseLike, AsyncIterator[Any]]:
        return await self._agent.arun(**kwargs)


def adapt_agent(agent: Agent) -> AgentRuntime:
    """Wrap an Agno ``Agent`` so it satisfies the :class:`AgentRuntime` Protocol."""
    return AgnoAgentRuntime(agent)  # type: ignore[return-value]


__all__ = ["AgnoAgentRuntime", "adapt_agent"]
