"""Unified parameter resolution for runtime + admin test execution (Phase 7 / F-09).

The legacy ``_read_param_value`` lived in three places (api/script builders,
test harness) with subtly different rules. This module is the single source
of truth.

Rules, in order, for resolving ``param_name``:
  1. Try, in ``call_locals``, the keys ``[name, snake(name), camel(name)]``.
  2. Try the same three keys in ``session_state``.
  3. If ``name`` (canonicalised to snake) ends in ``_id`` AND it is the *only*
     ``*_id`` declared by the tool AND no explicit ``id`` param is declared,
     fall back to ``call_locals["id"]``.
  4. If ``name`` ends in ``_id``, fall back to ``call_locals["<base>_number"]``
     and then ``session_state["<base>_number"]``.
  5. Return ``None``.
"""
from __future__ import annotations

import keyword
import re
from typing import Any, Iterable, Mapping, MutableMapping, Optional


def to_snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def to_camel_case(value: str) -> str:
    parts = value.split("_")
    if not parts:
        return value
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def is_valid_identifier(value: str) -> bool:
    return bool(value) and value.isidentifier() and not keyword.iskeyword(value)


class ToolParameterResolver:
    """Resolves named tool parameters from invocation locals + session state.

    Instances are cheap; build one per tool invocation.
    """

    def __init__(
        self,
        *,
        declared_param_names: Iterable[str],
        call_locals: Mapping[str, Any],
        session_state: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._call_locals: Mapping[str, Any] = call_locals
        self._session_state: Mapping[str, Any] = session_state or {}

        canonical: set[str] = set()
        for raw in declared_param_names:
            if isinstance(raw, str) and raw:
                canonical.add(to_snake_case(raw))
        self._canonical_names: frozenset[str] = frozenset(canonical)
        self._id_like_names: frozenset[str] = frozenset(
            name for name in canonical if name.endswith("_id")
        )
        self._has_explicit_id: bool = "id" in canonical

    @property
    def canonical_names(self) -> frozenset[str]:
        return self._canonical_names

    def resolve(self, param_name: str) -> Any:
        """Return the resolved value for ``param_name`` or ``None``."""
        candidates = (param_name, to_snake_case(param_name), to_camel_case(param_name))

        for candidate in candidates:
            value = self._call_locals.get(candidate) if candidate in self._call_locals else None
            if value is not None:
                return value

        for candidate in candidates:
            value = self._session_state.get(candidate) if candidate in self._session_state else None
            if value is not None:
                return value

        canonical = to_snake_case(param_name)

        if (
            canonical.endswith("_id")
            and len(self._id_like_names) == 1
            and canonical in self._id_like_names
            and not self._has_explicit_id
        ):
            generic_id = self._call_locals.get("id")
            if generic_id is not None:
                return generic_id

        if canonical.endswith("_id"):
            number_alias = f"{canonical[:-3]}_number"
            value = self._call_locals.get(number_alias)
            if value is not None:
                return value
            value = self._session_state.get(number_alias)
            if value is not None:
                return value

        return None

    def resolve_all(self, names: Iterable[str]) -> dict[str, Any]:
        return {name: self.resolve(name) for name in names}


def collect_id_like_aliases(canonical_names: Iterable[str]) -> frozenset[str]:
    return frozenset(name for name in canonical_names if name.endswith("_id"))


__all__ = [
    "ToolParameterResolver",
    "collect_id_like_aliases",
    "is_valid_identifier",
    "to_camel_case",
    "to_snake_case",
]
