import json
from typing import Any

from api.errors import BadRequestError
from setup.translator import trans


# ---------------------------------------------------------------------------
# Per-entity JSON column lists used by :func:`normalize_payload`.
#
# WARNING — keep this table in sync with the actual repository schemas:
#   - When you add a new entity (node / tool / mcp_server / ...), add an
#     entry here AND in the matching ``database/schemas/...`` definition.
#   - When you add a new JSON-shaped column to an existing entity, add
#     its column name to the matching set below.
#
# Full migration to per-entity pydantic schemas (with field-level
# serialisers) is tracked under A-08 / Phase 13 as out of scope —
# the breadth of 10 entities and their downstream serialisers makes
# that a multi-phase effort. This declarative table is the
# documented quick win: every JSON field flows through one encoder.
# ---------------------------------------------------------------------------
_JSON_FIELDS_BY_ENTITY: dict[str, set[str]] = {
    "node": {"runtime_config_json", "metadata_json"},
    "edge": {"member_instructions_json", "metadata_json"},
    "tool": {"user_types", "parameters", "required_tool_ids", "api_headers", "metadata_json"},
    "action": {"constructor_params", "metadata_json"},
    "tool_action_binding": {"constructor_params", "metadata_json"},
    "node_tool_binding": {"metadata_json"},
    "mcp_server": {"env_json", "headers_json", "include_tools_json", "exclude_tools_json", "metadata_json"},
    "node_mcp_binding": {"header_template_json", "metadata_json"},
    "skill": {"metadata_json"},
    "node_skill_binding": {"metadata_json"},
    "agent_channel": {"metadata_json"},
}


def encode_json_field(value: Any) -> Any:
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def normalize_payload(entity: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Serialise the JSON columns of ``entity`` to text-encoded strings.

    Raises ``KeyError`` early when ``entity`` is not a registered name —
    silently returning an empty set previously masked typos.
    """
    if entity not in _JSON_FIELDS_BY_ENTITY:
        raise KeyError(
            f"normalize_payload: unknown entity '{entity}'. "
            f"Registered entities: {sorted(_JSON_FIELDS_BY_ENTITY.keys())}"
        )
    normalized = dict(payload)
    for field_name in _JSON_FIELDS_BY_ENTITY[entity]:
        if field_name in normalized:
            normalized[field_name] = encode_json_field(normalized[field_name])
    return normalized


def coerce_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise BadRequestError(trans("errors.platform.admin.field_must_be_integer", field_name=field_name))
    if isinstance(value, int):
        return value

    text_value = str(value).strip()
    if not text_value.isdigit():
        raise BadRequestError(trans("errors.platform.admin.field_must_be_integer", field_name=field_name))
    return int(text_value)
