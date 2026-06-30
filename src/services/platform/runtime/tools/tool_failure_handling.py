import json
import re
from typing import Any, Optional

from setup.enums import ToolErrorStatusEnum


_SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE)\b", re.IGNORECASE),
    re.compile(r"Executed Query", re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE),
    re.compile(r"File \".+?\", line \d+", re.IGNORECASE),
    re.compile(r"(?:asyncpg|psycopg|sqlalchemy|backbone_orm)\.", re.IGNORECASE),
    re.compile(r"\bFROM\s+\"?\w+\"?\.\"?\w+\"?", re.IGNORECASE),
    re.compile(r"\bINTO\s+\"?\w+\"?\.\"?\w+\"?", re.IGNORECASE),
)

_GENERIC_TOOL_FAILURE_MESSAGE = "tool_internal_error"


def _is_sensitive_text(text: str) -> bool:
    """Return True if ``text`` looks like a DB/driver error or stack trace.

    We sanitize anything that exposes SQL, schema/table names, traceback
    frames, or driver internals — these must never be forwarded to the
    chat, regardless of which tool emitted them.
    """
    if not text:
        return False
    sample = text[:2000]
    return any(p.search(sample) for p in _SENSITIVE_PATTERNS)



_FAILURE_STATUSES: frozenset[str] = frozenset(
    {member.value for member in ToolErrorStatusEnum}
    | {
        "failed",
        "failure",
        "invalid_request",
        "validation_error",
        "cancelled",
        "canceled",
        "timeout",
        "timed_out",
        "provider_error",
    }
)


def mark_tool_execution_failed(
    *,
    agent: Any = None,
    session_state: Optional[dict] = None,
    reason: Optional[str] = None,
    error: Optional[Any] = None,
) -> Optional[dict]:
    resolved_state = session_state
    if not isinstance(resolved_state, dict):
        agent_state = getattr(agent, "session_state", None)
        resolved_state = agent_state if isinstance(agent_state, dict) else None

    if resolved_state is None and agent is not None:
        resolved_state = {}
        agent.session_state = resolved_state

    if not isinstance(resolved_state, dict):
        return None

    resolved_state["tool_execution_failed"] = True
    if reason:
        resolved_state["tool_execution_failure_reason"] = str(reason).strip()
    if error is not None:
        error_text = str(error).strip()
        if error_text:
            if _is_sensitive_text(error_text):
                error_text = _GENERIC_TOOL_FAILURE_MESSAGE
            resolved_state["tool_execution_failure_error"] = error_text[:1000]

    if agent is not None:
        agent.session_state = resolved_state
    return resolved_state


def stringify_tool_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)
    return str(result)


def extract_tool_failure_message(result: Any) -> Optional[str]:
    payload = _object_to_dict(result)
    if payload:
        payload_failure = _extract_payload_failure(payload)
        if payload_failure:
            return payload_failure
    text = stringify_tool_result(result).strip()
    if not text:
        return None
    parsed_payload = _parse_text_payload(text)
    if parsed_payload:
        payload_failure = _extract_payload_failure(parsed_payload)
        if payload_failure:
            return payload_failure
    return None


def _parse_text_payload(text: str) -> dict:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return {}
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_failure_text(value: Any, fallback: str) -> str:
    """Return ``value`` as a string, replaced with ``fallback`` if it
    contains DB/driver/stack-trace fragments.
    """
    text = stringify_tool_result(value)
    if _is_sensitive_text(text):
        return fallback
    return text or fallback


def _extract_payload_failure(payload: dict) -> Optional[str]:
    if payload.get("success") is False:
        msg = _payload_message(payload)
        return msg or "tool returned success=false"
    status = str(payload.get("status") or payload.get("run_status") or payload.get("state") or "").strip().lower()
    if status in _FAILURE_STATUSES:
        msg = _payload_message(payload)
        return msg or f"tool returned status={status}"
    errors = payload.get("errors")
    if errors not in (None, "", [], {}):
        has_renderable_content = any(payload.get(key) not in (None, "", [], {}) for key in ("items", "blocks", "data"))
        if not isinstance(payload.get("ui_component"), str) or not has_renderable_content:
            return _safe_failure_text(errors, _GENERIC_TOOL_FAILURE_MESSAGE)
    for key in ("error", "exception", "traceback"):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return _safe_failure_text(value, _GENERIC_TOOL_FAILURE_MESSAGE)
    return None


def _payload_message(payload: dict) -> str:
    for key in ("message", "detail", "reason", "error", "exception"):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return _safe_failure_text(value, _GENERIC_TOOL_FAILURE_MESSAGE)
    return ""


def _object_to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            return {}
    if hasattr(value, "dict"):
        try:
            dumped = value.dict()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            return {}
    if hasattr(value, "__dict__"):
        try:
            return {key: val for key, val in value.__dict__.items() if not str(key).startswith("_")}
        except Exception:
            return {}
    return {}
