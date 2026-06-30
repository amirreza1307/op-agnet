"""Raw agent run orchestration."""
from __future__ import annotations

import logging
from typing import Any, Optional

from api.errors import ServiceUnavailableError
from setup.translator import trans

log = logging.getLogger(__name__)


class AgentOrchestrator:
    """Thin facade over an AgentRuntime for one-shot runs."""

    @staticmethod
    async def run(
        runtime_target: Any,
        *,
        message: str,
        user_id: Optional[str],
        session_id: Optional[str],
        session_state: dict[str, Any],
        stream_events: Optional[bool],
        output_schema: Any,
    ) -> Any:
        run_response = await runtime_target.arun(
            input=message,
            user_id=user_id,
            session_id=session_id,
            session_state=dict(session_state),
            stream=False,
            stream_events=stream_events,
            output_schema=output_schema,
        )
        AgentOrchestrator._ensure_successful_run(run_response)
        return run_response

    @staticmethod
    def _ensure_successful_run(run_response: Any) -> None:
        status = getattr(run_response, "status", None)
        status_value = getattr(status, "value", status)
        if str(status_value or "").lower() == "completed":
            return
        content = getattr(run_response, "content", None)
        if content is None and hasattr(run_response, "get_content_as_string"):
            content = run_response.get_content_as_string()
        raise ServiceUnavailableError(str(content or trans("errors.platform.runtime.runtime_failed")))
