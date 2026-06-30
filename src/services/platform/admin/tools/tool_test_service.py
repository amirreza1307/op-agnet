"""Admin-only tool execution harness.

Lets platform administrators invoke any registered tool (script / api / task-products)
with custom parameters and a synthetic ``session_state`` so the response shape can be
inspected from the admin UI.

The harness mirrors the runtime behaviour of :class:`DynamicToolFactory` but skips
the Agno wrapper — every action runs directly so the raw return values are surfaced.
The user auth context (cookie / authorization header / x-access-key) is forwarded
from the incoming admin request so that downstream tools that depend on the caller's
Basalam session continue to work.
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace
from typing import Any, Optional

import httpx

from api.errors import BadRequestError, NotFoundError
from database.repositories.main.tool_action_binding_repo import ToolActionBindingRepo
from database.repositories.main.tool_action_repo import ToolActionRepo
from database.repositories.main.tool_knowledge_node_repo import ToolKnowledgeNodeRepo
from database.repositories.main.tool_repo import ToolRepo
from services.platform.runtime.agno.runtime_context import (
    build_runtime_session_state,
    build_runtime_transport_headers,
)
from services.platform.runtime.tools.dynamic_tool_factory import (
    _effective_constructor_params,
    _interpolate_template,
    _is_interpolation_value,
    _to_camel_case,
    _to_snake_case,
)
from tools.registry import get_registration, get_service_class


_FORWARDED_AUTH_HEADER_NAMES = (
    "accept",
    "accept-language",
    "cache-control",
    "origin",
    "pragma",
    "priority",
    "referer",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "user-agent",
    "x-client-info",
    "x-creation-tags",
    "x-access-key",
    "x-api-key",
    "authorization",
    "cookie",
)


class ToolTestService:
    """Execute a tool record end-to-end for admin debugging."""

    @classmethod
    async def test_tool(
        cls,
        *,
        tool_id: Optional[int] = None,
        tool_slug: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        session_state: Optional[dict[str, Any]] = None,
        vendor_id: Optional[int] = None,
        principal_id: Optional[str] = None,
        session_id: Optional[str] = None,
        forwarded_auth_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        tool = await cls._resolve_tool(tool_id=tool_id, tool_slug=tool_slug)

        merged_session_state = build_runtime_session_state(
            session_state or {},
            vendor_id=vendor_id,
            principal_id=principal_id,
            session_id=session_id,
            forwarded_auth_headers=forwarded_auth_headers,
        )

        params = dict(parameters or {})
        runtime_target = SimpleNamespace(
            session_state=merged_session_state,
            session_id=merged_session_state.get("current_session_id"),
        )

        started_at = time.perf_counter()
        try:
            if tool.tool_type == "api":
                result = await cls._run_api_tool(tool, params, runtime_target)
                actions_executed: list[dict[str, Any]] = []
            elif tool.tool_type == "knowledge":
                result = await cls._run_knowledge_tool(tool)
                actions_executed = []
            else:
                result, actions_executed = await cls._run_script_tool(tool, params, runtime_target)
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return {
                "ok": True,
                "tool_id": tool.id,
                "tool_slug": tool.slug,
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "duration_ms": round(elapsed_ms, 2),
                "session_state": cls._safe_session_state(merged_session_state),
                "parameters": params,
                "result": cls._safe_value(result),
                "actions_executed": actions_executed,
                "error": None,
            }
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return {
                "ok": False,
                "tool_id": tool.id,
                "tool_slug": tool.slug,
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "duration_ms": round(elapsed_ms, 2),
                "session_state": cls._safe_session_state(merged_session_state),
                "parameters": params,
                "result": None,
                "actions_executed": [],
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    # ------------------------------------------------------------------
    # Tool resolution
    # ------------------------------------------------------------------

    @staticmethod
    async def _resolve_tool(*, tool_id: Optional[int], tool_slug: Optional[str]):
        if tool_id is not None:
            tool = await ToolRepo.find_active_by_id(tool_id)
            if tool is None:
                raise NotFoundError(f"Tool {tool_id} does not exist or is inactive")
            return tool
        if tool_slug:
            tool = await ToolRepo.find_active_by_slug(tool_slug)
            if tool is None:
                raise NotFoundError(f"Tool '{tool_slug}' does not exist or is inactive")
            return tool
        raise BadRequestError("tool_id or tool_slug is required")

    # ------------------------------------------------------------------
    # knowledge tools
    # ------------------------------------------------------------------

    @classmethod
    async def _run_knowledge_tool(cls, tool) -> dict[str, Any]:
        nodes = await ToolKnowledgeNodeRepo.get_active_by_tool_slug(str(tool.slug or "").strip())
        return {
            "knowledge_nodes": [
                {
                    "title": node.title,
                    "content": node.content,
                    "priority": node.priority,
                }
                for node in nodes
            ],
            "tool_output": "",
        }

    # ------------------------------------------------------------------
    # script tools
    # ------------------------------------------------------------------

    @classmethod
    async def _run_script_tool(
        cls,
        tool,
        params: dict[str, Any],
        runtime_target: SimpleNamespace,
    ) -> tuple[Any, list[dict[str, Any]]]:
        bindings = await ToolActionBindingRepo.get_bindings_by_tool_id(tool.id)
        if not bindings:
            raise BadRequestError(
                f"Tool '{tool.name}' has no enabled action bindings to execute"
            )

        sorted_bindings = sorted(bindings, key=lambda b: getattr(b, "priority", 0) or 0)
        actions_executed: list[dict[str, Any]] = []
        last_result: Any = None

        for binding in sorted_bindings:
            action = await ToolActionRepo.find_active_by_id(binding.action_id)
            if action is None:
                raise BadRequestError(
                    f"Action {binding.action_id} bound to tool '{tool.name}' is missing or inactive"
                )

            service_cls = get_service_class(action.slug)
            constructor_kwargs = {"agent": runtime_target}
            constructor_params_mapping = _effective_constructor_params(
                service_cls,
                binding,
                tool.parameters or [],
            )
            for tool_param_name, constructor_param_name in constructor_params_mapping.items():
                constructor_kwargs[constructor_param_name] = cls._read_param_value(
                    tool_param_name, params, runtime_target.session_state
                )

            service_instance = service_cls(**constructor_kwargs)
            started_at = time.perf_counter()
            result = await service_instance.run()
            elapsed_ms = (time.perf_counter() - started_at) * 1000

            actions_executed.append(
                {
                    "action_id": action.id,
                    "action_slug": action.slug,
                    "name_fa": get_registration(action.slug).name_fa,
                    "constructor_kwargs": cls._safe_value(
                        {k: v for k, v in constructor_kwargs.items() if k != "agent"}
                    ),
                    "duration_ms": round(elapsed_ms, 2),
                    "result": cls._safe_value(result),
                }
            )
            last_result = result

        return last_result, actions_executed

    @staticmethod
    def _read_param_value(
        param_name: str,
        params: dict[str, Any],
        session_state: dict[str, Any],
    ) -> Any:
        candidates = [param_name, _to_snake_case(param_name), _to_camel_case(param_name)]
        for candidate in candidates:
            if candidate in params and params.get(candidate) not in (None, ""):
                return params.get(candidate)
        if isinstance(session_state, dict):
            for candidate in candidates:
                if candidate in session_state and session_state.get(candidate) not in (None, ""):
                    return session_state.get(candidate)
        return None

    # ------------------------------------------------------------------
    # api tools
    # ------------------------------------------------------------------

    @classmethod
    async def _run_api_tool(
        cls,
        tool,
        params: dict[str, Any],
        runtime_target: SimpleNamespace,
    ) -> dict[str, Any]:
        api_url = tool.api_url or ""
        api_method = (tool.api_method or "GET").upper()
        api_headers = tool.api_headers or {}
        api_body_template = tool.api_body_template
        tool_params = tool.parameters or []

        param_values: dict[str, Any] = {}
        session_state = dict(runtime_target.session_state or {})

        for param_def in tool_params:
            name = param_def.get("name", "")
            if not name:
                continue
            value = (
                params.get(name)
                or params.get(_to_snake_case(name))
                or params.get(_to_camel_case(name))
            )
            if value is None:
                value = (
                    session_state.get(name)
                    or session_state.get(_to_snake_case(name))
                    or session_state.get(_to_camel_case(name))
                )
            if value is not None:
                param_values[name] = value

        for key, value in session_state.items():
            if not isinstance(key, str) or key in param_values or value is None:
                continue
            if _is_interpolation_value(value):
                param_values[key] = value

        final_url = _interpolate_template(api_url, param_values)
        final_headers = build_runtime_transport_headers(session_state)
        for header_key, header_value in (api_headers or {}).items():
            final_headers[header_key] = _interpolate_template(str(header_value), param_values)

        # Forward the original auth headers (cookie, authorization, x-access-key, ...)
        # so downstream basalam endpoints honour the admin's session.
        forwarded = session_state.get("forwarded_auth_headers") or {}
        if isinstance(forwarded, dict):
            for header_key, header_value in forwarded.items():
                if header_key.lower() in ("host", "content-length", "transfer-encoding"):
                    continue
                final_headers.setdefault(header_key, str(header_value))

        final_body: Any = None
        if api_body_template:
            interpolated = _interpolate_template(api_body_template, param_values)
            try:
                final_body = json.loads(interpolated)
            except json.JSONDecodeError:
                final_body = interpolated

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=api_method,
                url=final_url,
                headers=final_headers,
                json=final_body if isinstance(final_body, (dict, list)) else None,
                content=final_body if isinstance(final_body, str) else None,
            )

        try:
            body_json: Any = response.json()
            body_text = None
        except ValueError:
            body_json = None
            body_text = response.text

        return {
            "request": {
                "method": api_method,
                "url": final_url,
                "headers": cls._safe_value(final_headers),
                "body": cls._safe_value(final_body),
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body_json": cls._safe_value(body_json),
                "body_text": body_text,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def extract_forwarded_headers(cls, request) -> dict[str, str]:
        incoming = request.headers
        headers: dict[str, str] = {}
        for name in _FORWARDED_AUTH_HEADER_NAMES:
            value = str(incoming.get(name) or "").strip()
            if value:
                headers[name] = value
        return headers

    @staticmethod
    def _safe_value(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): ToolTestService._safe_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [ToolTestService._safe_value(v) for v in value]
        if hasattr(value, "model_dump"):
            try:
                return value.model_dump(mode="json")
            except Exception:
                pass
        if hasattr(value, "to_dict"):
            try:
                return value.to_dict()
            except Exception:
                pass
        try:
            return str(value)
        except Exception:
            return repr(value)

    @staticmethod
    def _safe_session_state(state: dict[str, Any]) -> dict[str, Any]:
        """Echo session_state back to the admin but redact the raw cookie blob."""
        cleaned = dict(state or {})
        forwarded = cleaned.get("forwarded_auth_headers")
        if isinstance(forwarded, dict):
            cleaned["forwarded_auth_headers"] = {
                key: ("***redacted***" if key.lower() in ("cookie", "authorization", "x-access-key", "x-api-key") else value)
                for key, value in forwarded.items()
            }
        return ToolTestService._safe_value(cleaned)
