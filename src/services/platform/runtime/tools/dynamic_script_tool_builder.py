"""Builder for ``script`` and action-only tool variants (Phase 2 — no ``exec``)."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from services.platform.runtime.tools.agno_function_builder import (
    ToolParam,
    ToolSpec,
    build_agno_function,
)
from services.platform.runtime.tools.dynamic_tool_helpers import (
    _effective_constructor_params,
    _format_tool_response,
    _resolve_runtime_target,
    _tool_show_result,
    _tool_stop_after_tool_call,
    _tool_stop_hooks,
    resolve_effective_tool_parameters,
)
from services.platform.runtime.tools.parameter_resolver import ToolParameterResolver
from services.platform.runtime.tools.tool_failure_handling import (
    extract_tool_failure_message,
    mark_tool_execution_failed,
    stringify_tool_result,
)
from services.platform.runtime.tools.tool_name_sanitizer import build_tool_description
from tools.registry import get_service_class

logger = logging.getLogger(__name__)


def resolve_action_service_class(action: Any):
    """Resolve a tool action's service class from its registry ``slug``."""
    return get_service_class(action.slug)


def _resolve_script_params(tool_record, service_classes) -> list[dict]:
    """Resolve script-tool parameters.

    For ``script`` tools the parameter list always comes from the bound action's
    Python ``Input`` schema (the DB ``parameters`` column is ignored); other tool
    types keep their DB-sourced parameters. ``param_type_overrides`` from the
    tool's ``metadata_json`` are applied in both cases. Delegates to
    :func:`resolve_effective_tool_parameters`.
    """
    action_slugs = [action.slug for _cls, action in service_classes]
    return resolve_effective_tool_parameters(
        tool_type=tool_record.tool_type,
        db_parameters=tool_record.parameters,
        action_slugs=action_slugs,
        metadata_json=getattr(tool_record, "metadata_json", None),
    )


def _to_tool_params(params: list[dict], actions: List[Any]) -> list[ToolParam]:
    tool_params: list[ToolParam] = []
    seen: set[str] = set()
    for param in params:
        if not isinstance(param, dict):
            continue
        name = str(param.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        raw_schema = param.get("schema")
        tool_params.append(
            ToolParam(
                name=name,
                type=str(param.get("type", "str")),
                default=param.get("default"),
                required=bool(param.get("required", False)),
                description=param.get("description"),
                schema=raw_schema if isinstance(raw_schema, dict) else None,
            )
        )
    for action in actions:
        for raw_name in (getattr(action, "constructor_params", {}) or {}).keys():
            name = str(raw_name).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            tool_params.append(ToolParam(name=name, type="str", default=None, required=False))
    return tool_params


def build_script_tool(
    tool_record,
    actions: List[Any],
    *,
    provider_name: str,
    force_direct_response: bool = False,
):
    """Build a ``script`` tool as an Agno ``Function``."""
    service_classes = []
    for action in sorted(actions, key=lambda a: a.priority):
        cls = resolve_action_service_class(action)
        service_classes.append((cls, action))

    params = _resolve_script_params(tool_record, service_classes)
    tool_params = _to_tool_params(params, actions)
    description = build_tool_description(
        tool_record.description,
        display_name=tool_record.name,
        provider_name=provider_name,
    )

    entrypoint = _ScriptEntrypoint(service_classes=service_classes, params=params)
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


def build_action_only_tool(
    tool_record,
    actions: List[Any],
    cached_result: Optional[str],
    *,
    provider_name_for,
    force_direct_response: bool = False,
):
    """Build an action-only tool; returns ``None`` if there are no actions."""
    if not actions:
        return None

    service_classes = []
    for action in sorted(actions, key=lambda a: a.priority):
        cls = resolve_action_service_class(action)
        service_classes.append((cls, action))

    params = _resolve_script_params(tool_record, service_classes)
    tool_params = _to_tool_params(params, actions)

    display_name = tool_record.action_only_name or tool_record.name
    provider_name = provider_name_for(tool_record, display_name)
    description = build_tool_description(
        tool_record.action_only_description or tool_record.description,
        display_name=display_name,
        provider_name=provider_name,
    )

    entrypoint = _ScriptEntrypoint(
        service_classes=service_classes,
        params=params,
        cached_result=cached_result,
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


class _ScriptEntrypoint:
    """Executes one or more ``BaseToolService`` actions in priority order."""

    def __init__(
        self,
        *,
        service_classes: list[tuple[Any, Any]],
        params: list[dict],
        cached_result: Optional[str] = None,
    ) -> None:
        self.service_classes = service_classes
        self.params = params
        self._cached_result_pending: Optional[str] = cached_result

    async def __call__(
        self,
        kwargs: dict[str, Any],
        *,
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
    ) -> str:
        if self._cached_result_pending is not None:
            cached = self._cached_result_pending
            self._cached_result_pending = None
            return cached

        runtime_target = _resolve_runtime_target(agent, team, run_context, kwargs)
        session_state = (
            getattr(runtime_target, "session_state", None)
            if isinstance(getattr(runtime_target, "session_state", None), dict)
            else None
        )

        declared_names: list[str] = []
        for param in self.params or []:
            raw = param.get("name") if isinstance(param, dict) else None
            if isinstance(raw, str) and raw:
                declared_names.append(raw)
        for _cls, action in self.service_classes:
            for raw in (action.constructor_params or {}).keys():
                if isinstance(raw, str) and raw:
                    declared_names.append(raw)

        resolver = ToolParameterResolver(
            declared_param_names=declared_names,
            call_locals=kwargs,
            session_state=session_state,
        )

        data: list[dict[str, Any]] = []
        for service_cls, action in self.service_classes:
            constructor_kwargs: dict[str, Any] = {"agent": runtime_target}
            mapping = _effective_constructor_params(service_cls, action, self.params)
            for tool_param_name, constructor_param_name in mapping.items():
                constructor_kwargs[constructor_param_name] = resolver.resolve(tool_param_name)

            service_instance = service_cls(**constructor_kwargs)
            result = await service_instance.run()
            failure_message = extract_tool_failure_message(result)
            if failure_message:
                # The action returned a recoverable error payload (e.g. "no
                # similar product found"). This is NOT an internal failure: the
                # message is meant for the agent, not the user. Raising here
                # would let Agno swallow the exception (its generic branch logs
                # "Could not run function ..." and does not re-raise), so the
                # run ends with ``None`` reaching the user. Instead we return
                # the raw payload as the tool result. The stop-after post-hook
                # (``_stop_after_post_hook``) re-detects this failure via
                # ``extract_tool_failure_message`` and forces
                # ``stop_after_tool_call=False`` so the result loops back to the
                # agent instead of being sent straight to the user.
                mark_tool_execution_failed(
                    agent=runtime_target,
                    reason="tool_returned_error_result",
                    error=f"{action.slug}: {failure_message}",
                )
                return stringify_tool_result(result)

            if result is not None:
                data.append(
                    {
                        "title": action.response_title or "",
                        "content": stringify_tool_result(result),
                    }
                )

        return await _format_tool_response(data)


__all__ = [
    "build_action_only_tool",
    "build_script_tool",
    "resolve_action_service_class",
]
