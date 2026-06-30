"""Abstract base class for all tool services."""
from __future__ import annotations

import functools
import logging
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Type

from pydantic import BaseModel, ConfigDict

USER_SESSION_KEYS = ("principal_id", "principalId", "current_principal_id", "currentPrincipalId")
logger = logging.getLogger(__name__)


class ToolErrorStatusEnum(str, Enum):
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"
    ERROR = "error"


class ToolInputSchema(BaseModel):
    """Base class for tool input schemas."""

    model_config = ConfigDict(extra="allow")


class ToolOutputSchema(BaseModel):
    """Base class for tool output schemas."""

    model_config = ConfigDict(extra="allow")


class BaseToolService(metaclass=ABCMeta):
    """Base for every tool service in ``src/tools/``."""

    Input: Type[ToolInputSchema]
    Output: Type[ToolOutputSchema]
    _abstract: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", None) or cls.__dict__.get("_abstract", False):
            return
        if not hasattr(cls, "Input") or not (
            isinstance(cls.Input, type) and issubclass(cls.Input, ToolInputSchema)
        ):
            raise TypeError(
                f"{cls.__name__} must declare an 'Input' class "
                "inheriting from ToolInputSchema"
            )
        if not hasattr(cls, "Output") or not (
            isinstance(cls.Output, type) and issubclass(cls.Output, ToolOutputSchema)
        ):
            raise TypeError(
                f"{cls.__name__} must declare an 'Output' class "
                "inheriting from ToolOutputSchema"
            )
        cls._wrap_run_with_knowledge_nodes()

    @classmethod
    def _wrap_run_with_knowledge_nodes(cls) -> None:
        """Enrich every concrete tool result with DB-managed knowledge nodes.

        The registry decorator assigns ``__tool_slug__`` after class creation.
        It is therefore resolved when the wrapped method executes, not while
        ``__init_subclass__`` is running.
        """
        original_run = cls.__dict__.get("run")
        if original_run is None or getattr(original_run, "__knowledge_wrapped__", False):
            return

        @functools.wraps(original_run)
        async def wrapped_run(self: "BaseToolService", *args: Any, **kwargs: Any) -> Any:
            result = await original_run(self, *args, **kwargs)
            return await self._attach_knowledge_nodes(result)

        wrapped_run.__knowledge_wrapped__ = True
        cls.run = wrapped_run

    def __init__(self, agent: Any, **kwargs: Any) -> None:
        self.agent = agent
        self._tool_params = kwargs
        excluded = {"agent", "team", "run_context", "_extra_kwargs"}
        forwarded = {k: v for k, v in kwargs.items() if k not in excluded}
        self._validated_input = self.Input(**forwarded)

    @property
    def input(self) -> ToolInputSchema:
        """Validated input parameters."""
        return self._validated_input

    @abstractmethod
    async def run(self) -> dict[str, Any]:
        """Called by the platform when this tool is invoked."""

    @classmethod
    def get_input_schema(cls) -> dict[str, Any]:
        """JSON Schema for this tool's input."""
        return cls.Input.model_json_schema()

    @classmethod
    def get_output_schema(cls) -> dict[str, Any]:
        """JSON Schema for this tool's output."""
        return cls.Output.model_json_schema()

    def _session_int(self, keys: tuple[str, ...], label: str) -> int:
        """Resolve a positive int from agent.session_state. Raises ValueError(label) if missing."""
        session_state = getattr(self.agent, "session_state", None)
        if not isinstance(session_state, dict):
            raise ValueError(f"{label} context is missing")
        for key in keys:
            value = session_state.get(key)
            if value in (None, ""):
                continue
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                return parsed
        raise ValueError(f"{label} context is missing")

    def _user_id(self) -> int:
        """Resolve the current user id from the agent session state."""
        return self._session_int(USER_SESSION_KEYS, "User")

    def _principal_id(self) -> str | None:
        state = getattr(self.agent, "session_state", None) or {}
        for key in ("principal_id", "user_id", "principal"):
            value = state.get(key) if isinstance(state, dict) else None
            if value not in (None, ""):
                return str(value)
        return None

    def _session_id(self) -> str | None:
        state = getattr(self.agent, "session_state", None) or {}
        if not isinstance(state, dict):
            return None
        for key in (
            "current_session_id",
            "currentSessionId",
            "session_id",
            "sessionId",
            "session",
        ):
            value = state.get(key)
            if value not in (None, ""):
                return str(value)
        return None

    def _forwarded_auth_headers(self) -> dict[str, str]:
        """Return forwarded user auth headers from session state."""
        state = getattr(self.agent, "session_state", None) or {}
        if not isinstance(state, dict):
            return {}
        headers = state.get("forwarded_auth_headers")
        if isinstance(headers, dict):
            return {str(k).lower(): str(v) for k, v in headers.items() if v not in (None, "")}
        return {}

    async def _record_action_view(self, _payload: dict[str, Any]) -> None:
        """Compatibility no-op; vendor action logging is removed from agentic core."""
        return None

    async def _attach_knowledge_nodes(self, result: Any) -> Any:
        """Return a two-section result when active nodes exist for this tool.

        Error payloads remain untouched so runtime failure detection keeps its
        existing semantics. A database/read failure is also non-fatal: tool
        execution must not fail only because optional knowledge enrichment is
        temporarily unavailable.
        """
        if self._is_error_result(result):
            return result

        tool_slug = str(getattr(type(self), "__tool_slug__", "") or "").strip()
        if not tool_slug:
            return result

        try:
            from database.repositories.main.tool_knowledge_node_repo import (
                ToolKnowledgeNodeRepo,
            )

            nodes = await ToolKnowledgeNodeRepo.get_active_by_tool_slug(tool_slug)
        except Exception:
            logger.exception(
                "Could not load knowledge nodes for tool slug '%s'", tool_slug
            )
            return result

        if not nodes:
            return result

        return {
            "knowledge_nodes": [
                {
                    "title": node.title,
                    "content": node.content,
                    "priority": node.priority,
                }
                for node in nodes
            ],
            "tool_output": result,
        }

    @staticmethod
    def _is_error_result(result: Any) -> bool:
        if hasattr(result, "model_dump"):
            try:
                result = result.model_dump()
            except Exception:
                return False
        if not isinstance(result, dict):
            return False
        if result.get("success") is False:
            return True
        status = str(
            result.get("status")
            or result.get("run_status")
            or result.get("state")
            or ""
        ).strip().lower()
        failure_statuses = {
            item.value for item in ToolErrorStatusEnum
        } | {
            "failed",
            "failure",
            "invalid_request",
            "validation_error",
            "cancelled",
            "canceled",
            "timeout",
            "timed_out",
            "provider_error",
        }
        if status in failure_statuses:
            return True
        if result.get("errors") not in (None, "", [], {}):
            return True
        return any(
            result.get(key) not in (None, "", [], {})
            for key in ("error", "exception", "traceback")
        )

    def _error_payload(
        self,
        message: str,
        *,
        status: ToolErrorStatusEnum | str = ToolErrorStatusEnum.ERROR,
    ) -> dict[str, Any]:
        status_value = status.value if isinstance(status, ToolErrorStatusEnum) else status
        return {"status": status_value, "message": message}
