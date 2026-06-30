"""Default subscribers wired into the runtime event bus (Phase 10)."""
from __future__ import annotations

import logging
from typing import Optional

from services.platform.runtime.observability.event_bus import (
    AgentRunCompleted,
    AgentRunStarted,
    RuntimeEvent,
    RuntimeEventBus,
    ToolCallCompleted,
    ToolCallStarted,
    get_event_bus,
)

log = logging.getLogger("platform.runtime.metrics")
audit_log = logging.getLogger("platform.runtime.audit")


def metrics_subscriber(event: RuntimeEvent) -> None:
    if isinstance(event, AgentRunCompleted):
        log.info(
            "agent_run_metric node=%s session=%s duration_ms=%s success=%s",
            event.node_id,
            event.session_id,
            event.duration_ms,
            event.success,
        )
    elif isinstance(event, ToolCallCompleted):
        log.info(
            "tool_call_metric tool=%s id=%s duration_ms=%s success=%s",
            event.tool_name,
            event.tool_call_id,
            event.duration_ms,
            event.success,
        )


def audit_subscriber(event: RuntimeEvent) -> None:
    if isinstance(event, AgentRunStarted):
        audit_log.info(
            "agent_run_started node=%s slug=%s session=%s principal=%s",
            event.node_id,
            event.slug,
            event.session_id,
            event.principal_id,
        )
    elif isinstance(event, AgentRunCompleted):
        audit_log.info(
            "agent_run_completed node=%s slug=%s session=%s principal=%s success=%s error=%s",
            event.node_id,
            event.slug,
            event.session_id,
            event.principal_id,
            event.success,
            event.error,
        )


def register_default_subscribers(bus: Optional[RuntimeEventBus] = None) -> None:
    bus = bus or get_event_bus()
    bus.subscribe(None, metrics_subscriber)
    bus.subscribe(None, audit_subscriber)


__all__ = [
    "audit_subscriber",
    "metrics_subscriber",
    "register_default_subscribers",
]
