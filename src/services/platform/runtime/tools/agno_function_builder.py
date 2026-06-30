"""Build an Agno ``Function`` from a typed spec, without ``exec()`` (Phase 2 / F-01).

The legacy code used ``exec(func_code, namespace)`` to materialise a Python
``async def`` whose signature Agno could inspect. Agno only really needs
two things to register a tool:

  * a ``name`` and ``description`` string,
  * a ``parameters`` JSON Schema object,
  * an ``entrypoint`` coroutine.

Building the ``Function`` instance directly — as ``PlatformMCPTools.build_tools``
already does — sidesteps Agno's reflective parameter discovery entirely and
removes the security-sensitive ``exec`` path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional

from api.errors import ApiError
from services.platform.runtime.contracts.errors import AgentRuntimeError
from setup.translator import trans

try:
    from agno.tools.function import Function
except Exception:  # pragma: no cover - optional dep
    Function = None  # type: ignore[assignment]

try:
    import sentry_sdk
except Exception:  # pragma: no cover - optional dep
    sentry_sdk = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


_PYTHON_TYPE_TO_JSON_SCHEMA: dict[str, dict[str, Any]] = {
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "bool": {"type": "boolean"},
    "list": {"type": "array", "items": {}},
    "List[str]": {"type": "array", "items": {"type": "string"}},
    "List[int]": {"type": "array", "items": {"type": "integer"}},
    "dict": {"type": "object", "additionalProperties": True, "properties": {}},
    "Optional[str]": {"type": "string"},
    "Optional[int]": {"type": "integer"},
    "Optional[float]": {"type": "number"},
    "Optional[bool]": {"type": "boolean"},
    "Optional[list]": {"type": "array", "items": {}},
    "Optional[List[str]]": {"type": "array", "items": {"type": "string"}},
    "Optional[List[int]]": {"type": "array", "items": {"type": "integer"}},
    "Optional[dict]": {"type": "object", "additionalProperties": True, "properties": {}},
}


@dataclass
class ToolParam:
    """One declared parameter of a tool."""

    name: str
    type: str = "str"
    default: Any = None
    required: bool = False
    description: Optional[str] = None
    schema: Optional[dict[str, Any]] = None


@dataclass
class ToolSpec:
    """Everything ``AgnoFunctionBuilder.build`` needs to produce a tool.

    ``entrypoint`` must be an ``async`` callable with signature
    ``entrypoint(call_kwargs: dict, *, agent=None, team=None, run_context=None) -> str``.
    The builder wraps it so Agno calls it with its own keyword convention.
    """

    name: str
    description: str
    parameters: List[ToolParam] = field(default_factory=list)
    entrypoint: Callable[..., Awaitable[str]] = field(default=None)  # type: ignore[assignment]
    show_result: bool = False
    stop_after_tool_call: bool = False
    pre_hook: Optional[Callable[..., Any]] = None
    post_hook: Optional[Callable[..., Any]] = None


def _param_to_schema(param: ToolParam) -> dict[str, Any]:
    if param.schema is not None:
        # Model-typed param: use its full nested schema verbatim.
        schema = dict(param.schema)
    else:
        schema = dict(_PYTHON_TYPE_TO_JSON_SCHEMA.get(param.type, {"type": "string"}))
    if param.description and "description" not in schema:
        schema["description"] = param.description
    return schema


def build_parameters_schema(params: List[ToolParam]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in params:
        properties[param.name] = _param_to_schema(param)
        if param.required and param.default is None:
            required.append(param.name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def build_agno_function(spec: ToolSpec) -> Any:
    """Construct an Agno ``Function`` from a :class:`ToolSpec`.

    Raises ``RuntimeError`` if Agno is not installed.
    """
    if Function is None:
        raise RuntimeError(trans("errors.platform.runtime.agno_not_installed"))
    if spec.entrypoint is None:
        raise ValueError(f"ToolSpec for {spec.name!r} missing entrypoint")

    parameters_schema = build_parameters_schema(spec.parameters)

    async def _wrapped(
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
        **kwargs: Any,
    ) -> str:
        try:
            return await spec.entrypoint(  # type: ignore[misc]
                kwargs,
                agent=agent,
                team=team,
                run_context=run_context,
            )
        except (ApiError, AgentRuntimeError):
            raise
        except Exception as exc:
            logger.exception("tool_entrypoint_failed: tool=%s", spec.name)
            if sentry_sdk is not None:
                try:
                    sentry_sdk.capture_exception(exc)
                except Exception:  # noqa: BLE001
                    pass
            raise AgentRuntimeError(
                trans("errors.platform.runtime.tool_internal_error"),
                reason="tool_unhandled_exception",
            ) from None

    function = Function(
        name=spec.name,
        description=spec.description,
        parameters=parameters_schema,
        entrypoint=_wrapped,
        skip_entrypoint_processing=True,
    )

    function.show_result = bool(spec.show_result)
    function.stop_after_tool_call = bool(spec.stop_after_tool_call)
    if spec.pre_hook is not None:
        function.pre_hook = spec.pre_hook
    if spec.post_hook is not None:
        function.post_hook = spec.post_hook

    return function


__all__ = [
    "ToolParam",
    "ToolSpec",
    "build_agno_function",
    "build_parameters_schema",
]
