"""Application-level facade for agent runs."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from services.platform.graph.graph_validation_service import GraphValidationService
from services.platform.graph.node_registry_service import NodeRegistryService
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from services.platform.runtime.agno.runtime_context import build_runtime_session_state
from services.platform.runtime.nodes.node_runtime_builder import (
    BuiltNodeRuntime,
    NodeRuntimeBuilder,
)
from services.platform.runtime.observability.event_bus import (
    AgentRunCompleted,
    AgentRunStarted,
    get_event_bus,
)
from services.platform.runtime.orchestration import AgentOrchestrator
from services.platform.runtime.orchestration._serialization import serialize_content

log = logging.getLogger(__name__)


class PlatformRunService:
    """Public entry point for one-shot agent runs."""

    @staticmethod
    async def run(
        *,
        message: str,
        node_id: Optional[int] = None,
        slug: Optional[str] = None,
        vendor_id: Optional[int] = None,
        session_id: Optional[str] = None,
        principal_id: Optional[str] = None,
        context: Optional[dict] = None,
        instructions: Optional[list[str]] = None,
        stream_events: Optional[bool] = None,
        output_schema: Optional[dict] = None,
        structured_outputs: Optional[bool] = None,
        forwarded_auth_headers: Optional[dict[str, str]] = None,
    ) -> dict:
        node, built, session_state = await PlatformRunService._prepare(
            message=message,
            node_id=node_id,
            slug=slug,
            vendor_id=vendor_id,
            session_id=session_id,
            principal_id=principal_id,
            context=context,
            instructions=instructions,
            structured_outputs=structured_outputs,
            forwarded_auth_headers=forwarded_auth_headers,
        )
        effective_output_schema = built.forced_output_schema or output_schema

        bus = get_event_bus()
        started_at = time.monotonic()
        bus.publish(
            AgentRunStarted(
                node_id=node.id,
                slug=node.slug,
                session_id=session_id,
                principal_id=principal_id,
            )
        )

        success = True
        error_text: Optional[str] = None
        try:
            run_response = await AgentOrchestrator.run(
                built.runtime,
                message=message,
                user_id=principal_id,
                session_id=session_id,
                session_state=session_state,
                stream_events=stream_events,
                output_schema=effective_output_schema,
            )
        except Exception as exc:
            success = False
            error_text = str(exc)
            raise
        finally:
            bus.publish(
                AgentRunCompleted(
                    node_id=node.id,
                    slug=node.slug,
                    session_id=session_id,
                    principal_id=principal_id,
                    duration_ms=(time.monotonic() - started_at) * 1000.0,
                    success=success,
                    error=error_text,
                )
            )

        PlatformRunService._log_run_response(run_response, session_id=session_id)
        content = getattr(run_response, "content", None)
        if content is None and hasattr(run_response, "get_content_as_string"):
            content = run_response.get_content_as_string()
        status = getattr(run_response, "status", None)
        status_value = getattr(status, "value", status)

        return {
            "id": str(getattr(run_response, "run_id", None) or getattr(run_response, "id", "") or "") or None,
            "node_id": node.id,
            "slug": node.slug,
            "session_id": getattr(run_response, "session_id", session_id),
            "content": serialize_content(content),
            "status": str(status_value) if status_value is not None else None,
        }

    @staticmethod
    async def _prepare(
        *,
        message: str,  # noqa: ARG004 - included for future progress hooks
        node_id: Optional[int],
        slug: Optional[str],
        vendor_id: Optional[int],
        session_id: Optional[str],
        principal_id: Optional[str],
        context: Optional[dict],
        instructions: Optional[list[str]],
        structured_outputs: Optional[bool],
        forwarded_auth_headers: Optional[dict[str, str]],
    ) -> tuple[Any, BuiltNodeRuntime, dict[str, Any]]:
        await PlatformCacheManager.load()
        GraphValidationService.validate_existing_graph()
        node = await NodeRegistryService.resolve(node_id=node_id, slug=slug)
        session_state = build_runtime_session_state(
            context,
            vendor_id=vendor_id,
            principal_id=principal_id,
            session_id=session_id,
            forwarded_auth_headers=forwarded_auth_headers,
        )
        session_state["entry_node_id"] = node.id
        session_state["entry_node_slug"] = node.slug

        built = await NodeRuntimeBuilder.build_runtime(
            node=node,
            session_state=session_state,
            extra_instructions=instructions,
        )
        if (
            built.forced_structured_outputs is not None
            and hasattr(built.runtime, "structured_outputs")
        ):
            built.runtime.structured_outputs = built.forced_structured_outputs
        elif (
            structured_outputs is not None
            and hasattr(built.runtime, "structured_outputs")
        ):
            built.runtime.structured_outputs = structured_outputs

        return node, built, session_state

    @staticmethod
    def _log_run_response(run_response: Any, *, session_id: Optional[str]) -> None:
        try:
            messages_dump = getattr(run_response, "messages", None) or []
            log.info(
                "platform_run_response session=%s total_messages=%d from_history=%d roles=%s",
                getattr(run_response, "session_id", session_id),
                len(messages_dump),
                sum(1 for m in messages_dump if getattr(m, "from_history", False)),
                [getattr(m, "role", "?") for m in messages_dump[:20]],
            )
        except Exception:
            log.exception("platform_run_log_failed")


__all__ = ["PlatformRunService"]
