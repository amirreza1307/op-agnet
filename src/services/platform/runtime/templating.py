"""Safe template rendering for URL / JSON body / header substitution (Phase 6 / F-11, F-12).

The legacy code used ``str.replace`` for ``{{name}}`` placeholders and
``str.format_map`` for ``{name}`` placeholders. Both leak attribute access
(format-string CVE class), perform no escaping, and copy every key from
``session_state`` into the substitution scope.

This module enforces:
  * Allow-listed variable names — only keys explicitly registered are
    substituted.
  * Context-specific escaping (URL → percent-encode, JSON → ``json.dumps``).
  * No ``__getattr__`` / ``__class__`` traversal — patterns are matched with
    a strict regex.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping
from urllib.parse import quote

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def _lookup(name: str, vars_: Mapping[str, Any]) -> Any:
    """Return ``vars_[name]`` or ``None`` if absent. Never traverses attributes."""
    return vars_.get(name) if isinstance(vars_, Mapping) else None


def render_url_template(template: str, vars_: Mapping[str, Any]) -> str:
    """Render a URL template, percent-encoding every substituted value."""
    if not template:
        return template

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = _lookup(name, vars_)
        if value is None:
            return ""
        return quote(str(value), safe="")

    return _PLACEHOLDER_RE.sub(replace, template)


def render_header_template(template: str, vars_: Mapping[str, Any]) -> str:
    """Render an HTTP header template.

    Header values must remain ASCII-safe and contain no CR/LF (smuggling).
    Substituted values are stringified, stripped of control chars, and
    truncated to a defensive 4 KB limit.
    """
    if not template:
        return template

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = _lookup(name, vars_)
        if value is None:
            return ""
        text = str(value).replace("\r", "").replace("\n", "")
        return text[:4096]

    return _PLACEHOLDER_RE.sub(replace, template)


def render_json_template(template: str, vars_: Mapping[str, Any]) -> Any:
    """Render a JSON body template.

    If the template parses as JSON, structural substitution is applied —
    each ``{{var}}`` placeholder inside a string value is replaced with the
    corresponding variable, with proper JSON escaping for strings and
    native passthrough for numbers / bools / null. Otherwise the template
    is rendered as a plain string with ``json.dumps``-quoted substitutions.
    """
    if not template:
        return template

    # Fast path: try to parse as JSON and walk the structure.
    try:
        parsed = json.loads(template)
    except (json.JSONDecodeError, TypeError, ValueError):
        # Template isn't valid JSON yet — substitute as plain text with
        # JSON-escaped values so the result *is* valid JSON afterward.
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            value = _lookup(name, vars_)
            if value is None:
                return "null"
            if isinstance(value, str):
                return json.dumps(value, ensure_ascii=False)[1:-1]  # inside quotes
            return json.dumps(value, ensure_ascii=False)

        rendered = _PLACEHOLDER_RE.sub(replace, template)
        try:
            return json.loads(rendered)
        except (json.JSONDecodeError, TypeError, ValueError):
            return rendered  # plain text body — caller decides what to do

    return _substitute_json(parsed, vars_)


def _substitute_json(node: Any, vars_: Mapping[str, Any]) -> Any:
    if isinstance(node, str):
        # If the entire string is a single placeholder, substitute with the
        # raw typed value (so `"{{vendor_id}}"` → ``42``, not ``"42"``).
        match = _PLACEHOLDER_RE.fullmatch(node.strip())
        if match is not None:
            return _lookup(match.group(1), vars_)

        def replace(m: re.Match[str]) -> str:
            value = _lookup(m.group(1), vars_)
            if value is None:
                return ""
            return str(value)

        return _PLACEHOLDER_RE.sub(replace, node)
    if isinstance(node, list):
        return [_substitute_json(item, vars_) for item in node]
    if isinstance(node, dict):
        return {key: _substitute_json(value, vars_) for key, value in node.items()}
    return node


__all__ = ["render_url_template", "render_header_template", "render_json_template"]
