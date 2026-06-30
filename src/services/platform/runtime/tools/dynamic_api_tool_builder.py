"""Builder for ``api`` tool variants (Phase 2 — no ``exec``)."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from services.platform.runtime.agno.runtime_context import build_runtime_transport_headers
from services.platform.runtime.contracts.errors import ToolApiError
from services.platform.runtime.tools.agno_function_builder import (
    ToolParam,
    ToolSpec,
    build_agno_function,
)
from services.platform.runtime.tools.dynamic_tool_helpers import (
    _is_interpolation_value,
    _resolve_runtime_target,
    _tool_show_result,
    _tool_stop_after_tool_call,
    _tool_stop_hooks,
)
from services.platform.runtime.tools.parameter_resolver import (
    ToolParameterResolver,
    to_snake_case,
)
from services.platform.runtime.tools.tool_failure_handling import mark_tool_execution_failed
from services.platform.runtime.tools.tool_name_sanitizer import build_tool_description
from services.platform.runtime.templating import (
    render_header_template,
    render_json_template,
    render_url_template,
)

logger = logging.getLogger(__name__)


def build_api_tool(tool_record, *, provider_name: str, force_direct_response: bool = False):
    """Build an ``api``-type tool as an Agno ``Function`` (no ``exec``)."""
    params = tool_record.parameters or []
    tool_params = [
        ToolParam(
            name=str(p.get("name", "")),
            type=str(p.get("type", "str")),
            default=p.get("default"),
            required=bool(p.get("required", False)),
            description=p.get("description"),
        )
        for p in params
        if isinstance(p, dict) and p.get("name")
    ]
    description = build_tool_description(
        tool_record.description,
        display_name=tool_record.name,
        provider_name=provider_name,
    )

    api_url = tool_record.api_url or ""
    api_method = (tool_record.api_method or "GET").upper()
    api_headers = tool_record.api_headers or {}
    api_body_template = tool_record.api_body_template

    entrypoint = _ApiEntrypoint(
        api_url=api_url,
        api_method=api_method,
        api_headers=api_headers,
        api_body_template=api_body_template,
        tool_params=tool_params,
    )

    stop_after = _tool_stop_after_tool_call(tool_record, force_direct_response=force_direct_response)
    spec = ToolSpec(
        name=provider_name,
        description=description,
        parameters=tool_params,
        entrypoint=entrypoint,
        show_result=_tool_show_result(tool_record, force_direct_response=force_direct_response),
        stop_after_tool_call=stop_after,
        **_tool_stop_hooks(stop_after),
    )
    return build_agno_function(spec)


class _ApiEntrypoint:
    """Callable that performs the actual HTTP request when Agno invokes the tool."""

    def __init__(
        self,
        *,
        api_url: str,
        api_method: str,
        api_headers: dict[str, Any],
        api_body_template: Any,
        tool_params: list[ToolParam],
    ) -> None:
        self.api_url = api_url
        self.api_method = api_method
        self.api_headers = api_headers or {}
        self.api_body_template = api_body_template
        self.declared_param_names = [p.name for p in tool_params]

    async def __call__(
        self,
        kwargs: dict[str, Any],
        *,
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
    ) -> str:
        runtime_target = _resolve_runtime_target(agent, team, run_context, kwargs)
        session_state = dict(getattr(runtime_target, "session_state", {}) or {})

        resolver = ToolParameterResolver(
            declared_param_names=self.declared_param_names,
            call_locals=kwargs,
            session_state=session_state,
        )

        param_values: dict[str, Any] = {}
        for name in self.declared_param_names:
            value = resolver.resolve(name)
            if value is not None:
                param_values[name] = value
                param_values.setdefault(to_snake_case(name), value)

        # Phase 6 / F-11: do NOT spill the entire session_state into the
        # interpolation scope. Only the canonical runtime context keys.
        for canonical in ("vendor_id", "principal_id", "current_session_id"):
            value = session_state.get(canonical)
            if value is not None and _is_interpolation_value(value):
                param_values.setdefault(canonical, value)

        runtime_session_id = getattr(runtime_target, "session_id", None)
        if runtime_session_id is not None:
            param_values.setdefault("current_session_id", runtime_session_id)

        final_url = render_url_template(self.api_url, param_values)
        final_headers = build_runtime_transport_headers(session_state)
        for header_key, header_value in self.api_headers.items():
            final_headers[header_key] = render_header_template(str(header_value), param_values)

        final_body: Any = None
        if self.api_body_template:
            final_body = render_json_template(self.api_body_template, param_values)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method=self.api_method,
                    url=final_url,
                    headers=final_headers,
                    json=final_body if isinstance(final_body, (dict, list)) else None,
                    content=(
                        final_body.encode("utf-8") if isinstance(final_body, str) else None
                    ),
                )
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as exc:
            body_excerpt = exc.response.text[:500] if exc.response is not None else ""
            message = f"HTTP {exc.response.status_code if exc.response else '?'}: {body_excerpt}"
            mark_tool_execution_failed(
                agent=runtime_target,
                reason="api_http_error",
                error=message,
            )
            raise ToolApiError(
                f"API call failed with {message}",
                status_code=exc.response.status_code if exc.response else None,
                reason="api_http_error",
                cause=exc,
            ) from exc
        except (ToolApiError, json.JSONDecodeError):
            raise
        except Exception as exc:
            mark_tool_execution_failed(
                agent=runtime_target,
                reason="api_request_error",
                error=str(exc),
            )
            raise ToolApiError(
                f"API call failed: {exc}",
                reason="api_request_error",
                cause=exc,
            ) from exc


__all__ = ["build_api_tool"]
