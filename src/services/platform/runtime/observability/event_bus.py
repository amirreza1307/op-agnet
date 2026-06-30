"""Lightweight in-process event bus for runtime lifecycle events (Phase 10 / ARCH-02)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Union

log = logging.getLogger(__name__)


@dataclass
class RuntimeEvent:
    """Base event."""

    event_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunStarted(RuntimeEvent):
    event_type: str = "agent_run_started"
    node_id: Optional[int] = None
    slug: Optional[str] = None
    session_id: Optional[str] = None
    principal_id: Optional[str] = None


@dataclass
class AgentRunCompleted(RuntimeEvent):
    event_type: str = "agent_run_completed"
    node_id: Optional[int] = None
    slug: Optional[str] = None
    session_id: Optional[str] = None
    principal_id: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class ToolCallStarted(RuntimeEvent):
    event_type: str = "tool_call_started"
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCallCompleted(RuntimeEvent):
    event_type: str = "tool_call_completed"
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True


Handler = Callable[[RuntimeEvent], Union[None, Awaitable[None]]]


class RuntimeEventBus:
    """In-process pub/sub. Subscribers may be sync or async; failures are isolated."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = {}
        self._wildcard: list[Handler] = []

    def subscribe(self, event_type: Optional[str], handler: Handler) -> None:
        if event_type is None:
            self._wildcard.append(handler)
            return
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: RuntimeEvent) -> None:
        """Fire-and-forget dispatch. Sync handlers run inline; async ones are scheduled."""
        handlers = self._subscribers.get(event.event_type, []) + self._wildcard
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    loop = self._safe_loop()
                    if loop is not None:
                        loop.create_task(self._await_handler(handler, event, result))
                    else:
                        # No loop — drop with a warning. Sync callers should
                        # register sync handlers.
                        log.warning(
                            "event_bus_async_handler_dropped event=%s reason=no_loop",
                            event.event_type,
                        )
            except Exception:
                log.exception(
                    "event_bus_handler_failed event=%s", event.event_type
                )

    @staticmethod
    def _safe_loop() -> Optional[asyncio.AbstractEventLoop]:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    @staticmethod
    async def _await_handler(
        handler: Handler, event: RuntimeEvent, coro: Awaitable[None]
    ) -> None:
        try:
            await coro
        except Exception:
            log.exception(
                "event_bus_async_handler_failed event=%s handler=%s",
                event.event_type,
                getattr(handler, "__qualname__", handler),
            )


_BUS = RuntimeEventBus()


def get_event_bus() -> RuntimeEventBus:
    return _BUS
