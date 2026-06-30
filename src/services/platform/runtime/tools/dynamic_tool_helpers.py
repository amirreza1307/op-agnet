"""Shared helpers for the dynamic tool factory."""
from __future__ import annotations

import keyword
import re
import types
import typing
from types import SimpleNamespace
from typing import Any, Iterable, List

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from services.platform.runtime.tools.tool_failure_handling import extract_tool_failure_message
from tools.base_tool import BaseToolService
from tools.registry import get_service_class

TYPE_MAP = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "list": "list",
    "dict": "dict",
    "any": "str",
    "Optional[str]": "Optional[str]",
    "Optional[int]": "Optional[int]",
    "Optional[float]": "Optional[float]",
    "Optional[bool]": "Optional[bool]",
    "Optional[list]": "Optional[list]",
    "Optional[dict]": "Optional[dict]",
    "Optional[List[str]]": "Optional[List[str]]",
    "Optional[List[int]]": "Optional[List[int]]",
    "List[str]": "List[str]",
    "List[int]": "List[int]",
}


_PYTHON_TYPE_TO_PARAM_TYPE = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool",
    list: "list",
    dict: "dict",
}


def _annotation_to_param_type(annotation: Any) -> str:
    """Map a Python type annotation onto the simple string used in tool ``parameters``.

    Strips ``Optional`` / ``Union`` wrappers and falls back to ``"str"`` for
    anything the dynamic factory cannot represent natively (e.g. ``Any`` or a
    custom pydantic model). Type information is only used to render the generated
    tool signature — the service-level pydantic ``Input`` schema still validates
    the real values at call time.
    """
    if annotation is None or annotation is type(None):  # noqa: E721
        return "str"
    if annotation is Any:
        return "str"
    if annotation in _PYTHON_TYPE_TO_PARAM_TYPE:
        return _PYTHON_TYPE_TO_PARAM_TYPE[annotation]

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is typing.Union or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if not non_none:
            return "str"
        # Prefer the most "structured" branch — list/dict beat int/float beat str —
        # so a Union like `list | str` still surfaces as `list` in the agent schema.
        priority = {"list": 4, "dict": 3, "int": 2, "float": 2, "bool": 2, "str": 1}
        best = "str"
        best_score = -1
        for arg in non_none:
            mapped = _annotation_to_param_type(arg)
            score = priority.get(mapped, 0)
            if score > best_score:
                best = mapped
                best_score = score
        return best

    if origin in (list, typing.List):  # type: ignore[attr-defined]
        return "list"
    if origin in (dict, typing.Dict):  # type: ignore[attr-defined]
        return "dict"

    return "str"


def _is_model(obj: Any) -> bool:
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def _model_object_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Inline JSON schema for a pydantic model, ``$defs`` resolved away.

    Providers expect a self-contained object schema (no ``$ref``/``$defs``), so
    we inline any nested ``$ref`` and drop the ``$defs`` block. Best-effort: on
    any failure the caller falls back to a flat type.
    """
    schema = model.model_json_schema(ref_template="#/$defs/{model}")
    defs = schema.pop("$defs", {})

    def _inline(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = defs.get(ref.split("/")[-1])
                if isinstance(target, dict):
                    return _inline({k: v for k, v in target.items()})
            return {k: _inline(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_inline(item) for item in node]
        return node

    return _inline(schema)


def _field_nested_schema(annotation: Any) -> dict[str, Any] | None:
    """Return a nested JSON schema for a pydantic-model field, else ``None``.

    Handles a direct ``BaseModel`` subclass → ``object`` schema, and
    ``list[BaseModel]`` (optionally inside a ``Union``/``Optional``) → ``array``
    schema whose ``items`` is the model's object schema. Anything else (plain
    primitives, ``dict``, ``Any``) returns ``None`` so the caller keeps the
    existing flat-type behaviour — this is what preserves parity for every tool
    that does not opt in with a model-typed field.
    """
    try:
        if _is_model(annotation):
            return _model_object_schema(annotation)

        origin = typing.get_origin(annotation)
        args = [a for a in typing.get_args(annotation) if a is not type(None)]

        if origin is typing.Union or origin is types.UnionType:
            # Prefer a model branch (``list[Model] | str`` → use the list[Model]).
            for arg in args:
                nested = _field_nested_schema(arg)
                if nested is not None:
                    return nested
            return None

        if origin in (list, typing.List):  # type: ignore[attr-defined]
            if len(args) == 1 and _is_model(args[0]):
                return {"type": "array", "items": _model_object_schema(args[0])}
    except Exception:
        return None
    return None


def extract_params_from_input_schema(service_cls) -> List[dict]:
    """Derive a ``parameters`` list from a ``BaseToolService.Input`` pydantic schema.

    Each entry has ``name``, ``type``, ``default`` and ``required`` keys, plus two
    optional keys:

    - ``description`` — when the Input field declares one via
      ``Field(description=...)``. Flows through ``_to_tool_params`` →
      ``ToolParam.description`` into the final JSON schema, so it is how a field
      documents itself to the LLM.
    - ``schema`` — a full nested JSON schema when the field is typed as a pydantic
      ``BaseModel`` (or ``list[BaseModel]``); see :func:`_field_nested_schema`. This
      lets a model-typed field surface its inner shape to the LLM instead of
      collapsing to a flat ``object``/``array``. ``type`` stays a flat string in
      that case (so DB-driven ``str(type)`` consumers are unaffected).

    Fields that are plain primitives/dicts emit neither extra key, so the output
    is byte-for-byte unchanged for every tool that does not opt in — preserving
    behaviour parity. Returns ``[]`` when the service isn't a ``BaseToolService``
    or has no Input fields.
    """
    try:
        if not issubclass(service_cls, BaseToolService):
            return []
    except TypeError:
        return []

    input_schema = getattr(service_cls, "Input", None)
    fields = getattr(input_schema, "model_fields", None) or {}
    if not fields:
        return []

    params: List[dict] = []
    for name, field in fields.items():
        default = field.default if field.default is not PydanticUndefined else None
        required = field.is_required()
        param: dict = {
            "name": name,
            "type": _annotation_to_param_type(field.annotation),
            "default": default,
            "required": required,
        }
        description = getattr(field, "description", None)
        if isinstance(description, str) and description.strip():
            param["description"] = description
        nested_schema = _field_nested_schema(field.annotation)
        if nested_schema is not None:
            param["schema"] = nested_schema
        params.append(param)
    return params


def _apply_param_type_overrides(params: List[dict], metadata_json: Any) -> List[dict]:
    """Apply ``param_type_overrides`` from a tool's ``metadata_json`` (if any)."""
    metadata = metadata_json or {}
    overrides = metadata.get("param_type_overrides") if isinstance(metadata, dict) else None
    if not (isinstance(overrides, dict) and overrides):
        return params
    result: List[dict] = []
    for param in params:
        if not isinstance(param, dict):
            result.append(param)
            continue
        override = overrides.get(param.get("name"))
        if override:
            param = {**param, "type": override}
        result.append(param)
    return result


def resolve_effective_tool_parameters(
    *,
    tool_type: str,
    db_parameters: Any,
    action_slugs: Iterable[str],
    metadata_json: Any = None,
) -> List[dict]:
    """Resolve the effective parameter list for a tool.

    For ``script`` tools the parameters ALWAYS come from the bound action's
    Python ``Input`` schema; the DB ``parameters`` column is ignored entirely.
    Among multiple actions, the first slug whose service class yields non-empty
    Input params wins (priority order is the caller's responsibility). When no
    slug resolves to params, an empty list is returned — there is no DB
    fallback for script tools by design.

    For ``api`` (and every other type) the DB ``parameters`` are returned
    unchanged.
    """
    if tool_type != "script":
        return list(db_parameters or [])

    params: List[dict] = []
    for slug in action_slugs:
        try:
            service_cls = get_service_class(slug)
        except Exception:
            # Unknown slug (UnknownToolSlug) or any resolution error: skip it.
            continue
        derived = extract_params_from_input_schema(service_cls)
        if derived:
            params = derived
            break

    return _apply_param_type_overrides(params, metadata_json)


def _to_camel_case(value: str) -> str:
    parts = value.split("_")
    if not parts:
        return value
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _to_snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def _is_valid_identifier(value: str) -> bool:
    return bool(value) and value.isidentifier() and not keyword.iskeyword(value)


def _resolve_param_type(raw_type: str, default) -> str:
    param_type = TYPE_MAP.get(raw_type, "str")
    if default is None and "Optional" not in param_type:
        return f"Optional[{param_type}]"
    return param_type


def _build_signature_params_for_tool(tool_name: str, params: List[dict], actions: List[object]) -> List[dict]:
    return list(params or [])


def _build_signature_parts(params: List[dict], actions: List[object]) -> List[str]:
    sig_parts = ["agent=None", "team=None", "run_context=None"]
    param_meta = {}
    ordered_params = []

    def add_param(name: str, type_name: str = "str", default=None):
        if name == "agent":
            return
        if not _is_valid_identifier(name):
            return
        if name in param_meta:
            return

        param_meta[name] = {
            "type_name": type_name or "str",
            "default": default,
        }
        ordered_params.append(name)

    for param in params:
        add_param(param.get("name", ""), param.get("type", "str"), param.get("default"))

    for action in actions:
        for tool_param_name in (action.constructor_params or {}).keys():
            add_param(str(tool_param_name))

    for name in ordered_params:
        meta = param_meta[name]
        param_type = _resolve_param_type(meta["type_name"], meta["default"])
        default = meta["default"]

        if default is None:
            sig_parts.append(f"{name}: {param_type} = None")
        elif isinstance(default, bool):
            sig_parts.append(f"{name}: {param_type} = {default}")
        elif isinstance(default, (int, float)):
            sig_parts.append(f"{name}: {param_type} = {default}")
        elif isinstance(default, str):
            sig_parts.append(f"{name}: {param_type} = {repr(default)}")
        else:
            sig_parts.append(f"{name}: {param_type} = {repr(default)}")

    sig_parts.append("**_extra_kwargs")

    return sig_parts


def _strip_extra_kwargs_from_schema(decorated, params: List[dict] | None = None):
    """Sanitize tool schema for provider compatibility."""
    schema = decorated.parameters or {}
    schema.get("properties", {}).pop("_extra_kwargs", None)
    schema.get("properties", {}).pop("agent", None)
    schema.get("properties", {}).pop("team", None)
    schema.get("properties", {}).pop("run_context", None)
    properties = schema.get("properties", {}) or {}

    for prop in properties.values():
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "array" and "items" not in prop:
            prop["items"] = {}
        elif prop_type == "object":
            if "properties" not in prop:
                prop["properties"] = {}
            if prop.get("additionalProperties") is False:
                prop["additionalProperties"] = True

    if params is not None:
        required_names = [
            p.get("name")
            for p in params
            if p.get("required") is True and p.get("name") in properties
        ]
        schema["required"] = required_names
    elif "required" in schema and isinstance(schema["required"], list):
        schema["required"] = [
            r for r in schema["required"]
            if r not in {"_extra_kwargs", "agent", "team", "run_context"} and r in properties
        ]

    decorated.parameters = schema
    decorated.skip_entrypoint_processing = True
    return decorated


async def _format_tool_response(data) -> str:
    if not data:
        return ""

    if len(data) == 1:
        return data[0]["content"]

    parts = []
    for item in data:
        title = item.get("title", "")
        content = item.get("content", "")
        if title and content:
            parts.append(f"{title} :\n{content}")
        elif content:
            parts.append(content)

    return "\n-----\n".join(parts)


def _tool_stop_after_tool_call(tool_record, *, force_direct_response: bool = False) -> bool:
    if force_direct_response:
        return True
    metadata = getattr(tool_record, "metadata_json", None) or {}
    return bool(metadata.get("stop_after_tool_call"))


def _tool_show_result(tool_record, *, force_direct_response: bool = False) -> bool:
    if force_direct_response:
        return True
    return bool(getattr(tool_record, "show_result", False))


def _stop_after_pre_hook(stop_after: bool):
    def _hook(fc):
        fc.function.stop_after_tool_call = stop_after
        import logging
        logging.getLogger(__name__).info(
            "stop_after pre_hook: tool=%s stop_after=%s",
            getattr(fc.function, "name", "?"), stop_after,
        )
    return _hook


def _stop_after_post_hook(stop_after: bool):
    def _hook(fc):
        import logging
        log = logging.getLogger(__name__)
        has_error = bool(fc.error)
        failure_msg = None
        try:
            failure_msg = extract_tool_failure_message(fc.result)
        except Exception as exc:
            log.warning("stop_after post_hook: failure_msg extraction raised: %r", exc)
        if has_error or failure_msg:
            fc.function.stop_after_tool_call = False
            log.info(
                "stop_after post_hook: tool=%s -> FALSE (has_error=%s failure=%r result_type=%s)",
                getattr(fc.function, "name", "?"), has_error, failure_msg, type(fc.result).__name__,
            )
        else:
            fc.function.stop_after_tool_call = stop_after
            log.info(
                "stop_after post_hook: tool=%s -> %s (clean, result_type=%s)",
                getattr(fc.function, "name", "?"), stop_after, type(fc.result).__name__,
            )
    return _hook


def _tool_stop_hooks(stop_after: bool) -> dict:
    return {
        "pre_hook": _stop_after_pre_hook(stop_after),
        "post_hook": _stop_after_post_hook(stop_after),
    }


def _resolve_runtime_target(agent, team, run_context, local_vars):
    target = agent or team
    if target is None and isinstance(local_vars, dict):
        extra_kwargs = local_vars.get("_extra_kwargs")
        if isinstance(extra_kwargs, dict):
            target = (
                extra_kwargs.get("agent")
                or extra_kwargs.get("team")
                or extra_kwargs.get("run_context")
                or extra_kwargs.get("context")
            )
        if target is None:
            target = (
                local_vars.get("team")
                or local_vars.get("agent")
                or local_vars.get("run_context")
            )

    if target is None:
        target = SimpleNamespace(session_state={}, session_id=None)

    if getattr(target, "session_state", None) is None and run_context is not None:
        run_context_state = getattr(run_context, "session_state", None)
        if isinstance(run_context_state, dict):
            target.session_state = run_context_state

    if target is not None and getattr(target, "session_state", None) is None:
        target.session_state = {}

    return target


def _iter_service_input_aliases(service_cls, params):
    """Yield same-name tool->constructor mappings for BaseToolService inputs.

    When ``params`` is empty (or missing names), fall back to every field on
    the service's ``Input`` schema — so script tools registered without an
    explicit parameter list still receive the right constructor kwargs.
    """
    try:
        if not issubclass(service_cls, BaseToolService):
            return
    except TypeError:
        return

    input_schema = getattr(service_cls, "Input", None)
    input_fields = getattr(input_schema, "model_fields", None) or {}
    if not input_fields:
        return

    param_names = []
    for param in params or []:
        raw_name = param.get("name", "") if isinstance(param, dict) else ""
        if isinstance(raw_name, str) and raw_name:
            param_names.append(raw_name)

    if not param_names:
        for field_name in input_fields.keys():
            yield field_name, field_name
        return

    for field_name in input_fields.keys():
        candidates = (field_name, _to_camel_case(field_name))
        for candidate in candidates:
            if candidate in param_names:
                yield candidate, field_name
                break


def _effective_constructor_params(service_cls, action, params):
    explicit = dict(getattr(action, "constructor_params", None) or {})
    mapped_constructor_names = set(explicit.values())
    effective = dict(explicit)
    inferred_aliases = list(_iter_service_input_aliases(service_cls, params))
    for tool_param_name, constructor_param_name in inferred_aliases:
        if constructor_param_name in mapped_constructor_names:
            continue
        effective.setdefault(tool_param_name, constructor_param_name)
        mapped_constructor_names.add(constructor_param_name)
    return effective


def _interpolate_template(template: str, params: dict) -> str:
    """Replace {{param_name}} placeholders with actual values."""
    if not template:
        return template
    result = template
    for key, value in params.items():
        if value is not None:
            result = result.replace("{{" + key + "}}", str(value))
    return result


def _is_interpolation_value(value) -> bool:
    return isinstance(value, (str, int, float, bool))
