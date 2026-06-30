"""Runtime context utilities (Phase 3 / F-02).

The historical session_state carried four aliases per identifier
(``vendor_id`` / ``vendorId`` / ``current_vendor_id`` / ``currentVendorId``)
which broke Single-Source-of-Truth and forced every reader to scan four
keys. This module now treats **snake_case as canonical** and the legacy
aliases are mirrored only for backward compatibility with old tool
definitions and external API templates that still use camelCase.

New code should:
  * Read the canonical keys: ``vendor_id``, ``principal_id``,
    ``current_session_id`` (matches Agno's own naming for session_id).
  * Use :class:`RuntimeContext` from
    ``services.platform.runtime.contracts.runtime_context`` for typed
    propagation.
"""
from __future__ import annotations

from typing import Any, Optional

_VENDOR_ID_KEYS = ("vendor_id", "vendorId", "current_vendor_id", "currentVendorId")
_SESSION_ID_KEYS = ("current_session_id", "currentSessionId", "session_id", "sessionId")
_PRINCIPAL_ID_KEYS = ("principal_id", "principalId", "current_principal_id", "currentPrincipalId")
FORWARDED_AUTH_HEADER_KEY = "forwarded_auth_headers"

_CANONICAL_VENDOR_KEY = "vendor_id"
_CANONICAL_PRINCIPAL_KEY = "principal_id"
_CANONICAL_SESSION_KEY = "current_session_id"

_CAMEL_VENDOR_KEY = "vendorId"
_CAMEL_PRINCIPAL_KEY = "principalId"
_CAMEL_SESSION_KEY = "currentSessionId"


def build_runtime_session_state(
    context: Optional[dict[str, Any]],
    *,
    vendor_id: Optional[int] = None,
    principal_id: Optional[str] = None,
    session_id: Optional[str] = None,
    forwarded_auth_headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Materialise a session_state dict.

    Canonical snake_case keys are always set; camelCase aliases are
    mirrored for legacy templates only. Old "current_*" prefixed legacy
    keys are kept for the session id alone (the field that genuinely had
    that name from the start).
    """
    state = dict(context or {})

    resolved_vendor_id = _resolve_positive_int(vendor_id, state, _VENDOR_ID_KEYS)
    if resolved_vendor_id is not None:
        state[_CANONICAL_VENDOR_KEY] = resolved_vendor_id
        state[_CAMEL_VENDOR_KEY] = resolved_vendor_id  # legacy alias
        state["current_vendor_id"] = resolved_vendor_id  # legacy alias
        state["currentVendorId"] = resolved_vendor_id  # legacy alias

    resolved_principal_id = _resolve_text(principal_id, state, _PRINCIPAL_ID_KEYS)
    if resolved_principal_id is not None:
        state[_CANONICAL_PRINCIPAL_KEY] = resolved_principal_id
        state[_CAMEL_PRINCIPAL_KEY] = resolved_principal_id  # legacy alias
        state["current_principal_id"] = resolved_principal_id  # legacy alias
        state["currentPrincipalId"] = resolved_principal_id  # legacy alias

    resolved_session_id = _resolve_text(session_id, state, _SESSION_ID_KEYS)
    if resolved_session_id is not None:
        state[_CANONICAL_SESSION_KEY] = resolved_session_id
        state[_CAMEL_SESSION_KEY] = resolved_session_id  # legacy alias

    if forwarded_auth_headers:
        cleaned = {
            str(k).lower(): str(v)
            for k, v in forwarded_auth_headers.items()
            if v not in (None, "")
        }
        if cleaned:
            state[FORWARDED_AUTH_HEADER_KEY] = cleaned

    return state


def to_session_state_adapter(state: dict[str, Any], *, style: str = "camel") -> dict[str, Any]:
    """Adapter used at boundaries that still expect camelCase keys.

    ``style="camel"`` returns an additive map; ``style="snake"`` returns a
    pure snake_case projection.
    """
    if style not in {"camel", "snake"}:
        raise ValueError(f"unknown style {style!r}")
    if style == "snake":
        return {
            k: v
            for k, v in state.items()
            if k
            in {
                _CANONICAL_VENDOR_KEY,
                _CANONICAL_PRINCIPAL_KEY,
                _CANONICAL_SESSION_KEY,
                "entry_node_id",
                "entry_node_slug",
                FORWARDED_AUTH_HEADER_KEY,
            }
        }
    mirror: dict[str, Any] = dict(state)
    if _CANONICAL_VENDOR_KEY in state:
        mirror.setdefault(_CAMEL_VENDOR_KEY, state[_CANONICAL_VENDOR_KEY])
    if _CANONICAL_PRINCIPAL_KEY in state:
        mirror.setdefault(_CAMEL_PRINCIPAL_KEY, state[_CANONICAL_PRINCIPAL_KEY])
    if _CANONICAL_SESSION_KEY in state:
        mirror.setdefault(_CAMEL_SESSION_KEY, state[_CANONICAL_SESSION_KEY])
    return mirror


def get_runtime_session_state(
    *,
    run_context: Any = None,
    agent: Any = None,
    team: Any = None,
) -> dict[str, Any]:
    if run_context is not None and isinstance(getattr(run_context, "session_state", None), dict):
        return dict(run_context.session_state)
    if agent is not None and isinstance(getattr(agent, "session_state", None), dict):
        return dict(agent.session_state)
    if team is not None and isinstance(getattr(team, "session_state", None), dict):
        return dict(team.session_state)
    return {}


def build_runtime_transport_headers(session_state: Optional[dict[str, Any]]) -> dict[str, str]:
    state = dict(session_state or {})
    headers: dict[str, str] = {}

    vendor_id = _resolve_positive_int(None, state, _VENDOR_ID_KEYS)
    if vendor_id is not None:
        headers["x-vendor-id"] = str(vendor_id)

    session_id = _resolve_text(None, state, _SESSION_ID_KEYS)
    if session_id is not None:
        headers["x-session-id"] = session_id

    principal_id = _resolve_text(None, state, _PRINCIPAL_ID_KEYS)
    if principal_id is not None:
        headers["x-principal-id"] = principal_id

    return headers


def build_runtime_env(session_state: Optional[dict[str, Any]]) -> dict[str, str]:
    state = dict(session_state or {})
    env: dict[str, str] = {}

    vendor_id = _resolve_positive_int(None, state, _VENDOR_ID_KEYS)
    if vendor_id is not None:
        env["VENDOR_ID"] = str(vendor_id)
        env["CURRENT_VENDOR_ID"] = str(vendor_id)

    session_id = _resolve_text(None, state, _SESSION_ID_KEYS)
    if session_id is not None:
        env["SESSION_ID"] = session_id
        env["CURRENT_SESSION_ID"] = session_id

    principal_id = _resolve_text(None, state, _PRINCIPAL_ID_KEYS)
    if principal_id is not None:
        env["PRINCIPAL_ID"] = principal_id
        env["CURRENT_PRINCIPAL_ID"] = principal_id

    return env


def build_mcp_runtime_arguments(
    parameters: Optional[dict[str, Any]],
    session_state: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Inject canonical runtime context as kwargs for an MCP tool call.

    The MCP tool's JSON schema declares which keys it accepts. We try the
    canonical key first, then the camelCase alias if the tool declares it
    that way. We do NOT inject all four aliases (legacy behaviour) — the
    canonical key is preferred, with one camelCase fallback per identifier.
    """
    properties = (parameters or {}).get("properties")
    if not isinstance(properties, dict):
        return {}

    state = dict(session_state or {})
    vendor_id = _resolve_positive_int(None, state, _VENDOR_ID_KEYS)
    session_id = _resolve_text(None, state, _SESSION_ID_KEYS)
    principal_id = _resolve_text(None, state, _PRINCIPAL_ID_KEYS)

    candidates: list[tuple[str, str, Any]] = [
        (_CANONICAL_VENDOR_KEY, _CAMEL_VENDOR_KEY, vendor_id),
        ("current_vendor_id", "currentVendorId", vendor_id),
        (_CANONICAL_SESSION_KEY, _CAMEL_SESSION_KEY, session_id),
        ("session_id", "sessionId", session_id),
        (_CANONICAL_PRINCIPAL_KEY, _CAMEL_PRINCIPAL_KEY, principal_id),
        ("current_principal_id", "currentPrincipalId", principal_id),
    ]

    resolved: dict[str, Any] = {}
    for canonical_key, camel_key, value in candidates:
        if value is None:
            continue
        if canonical_key in properties:
            resolved.setdefault(canonical_key, value)
        elif camel_key in properties:
            resolved.setdefault(camel_key, value)
    return resolved


def _resolve_positive_int(
    explicit_value: Any,
    state: dict[str, Any],
    keys: tuple[str, ...],
) -> Optional[int]:
    candidate = explicit_value
    if candidate is None:
        for key in keys:
            if key in state and state.get(key) not in (None, ""):
                candidate = state.get(key)
                break

    if candidate in (None, ""):
        return None
    if isinstance(candidate, bool):
        return None
    if isinstance(candidate, int):
        return candidate if candidate > 0 else None

    text = str(candidate).strip()
    if text.isdigit():
        value = int(text)
        return value if value > 0 else None
    return None


def _resolve_text(
    explicit_value: Any,
    state: dict[str, Any],
    keys: tuple[str, ...],
) -> Optional[str]:
    candidate = explicit_value
    if candidate is None:
        for key in keys:
            if key in state and state.get(key) not in (None, ""):
                candidate = state.get(key)
                break

    if candidate in (None, ""):
        return None
    text = str(candidate).strip()
    return text or None
