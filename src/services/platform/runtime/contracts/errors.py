"""Exception hierarchy for the platform runtime (Phase 9 / F-06)."""
from __future__ import annotations

from typing import Any, Optional


class AgentRuntimeError(RuntimeError):
    """Base class for every failure that originates inside the runtime."""

    def __init__(self, message: str, *, reason: Optional[str] = None, cause: Any = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.cause = cause


class ToolExecutionError(AgentRuntimeError):
    """A bound tool failed to execute."""


class ToolValidationError(ToolExecutionError):
    """A tool was invoked with arguments that violated its contract."""


class ToolApiError(ToolExecutionError):
    """An ``api``-type tool received a non-2xx response or transport error."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code


class ToolScriptError(ToolExecutionError):
    """A ``script``-type tool action raised or returned a failure payload."""


class McpSessionError(AgentRuntimeError):
    """The MCP transport / session layer failed to provide a usable session."""
