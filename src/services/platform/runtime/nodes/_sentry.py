"""Loud failure reporting for node-runtime tool assembly.

Building a node's tool list is *defensive*: a misconfigured tool must not crash
the whole run, so the builder skips it and keeps going. But a silent skip is its
own hazard — a ``script`` tool that resolves to **zero actions** is still a valid
function the model can call; it just returns an empty string, which makes the
agent answer with nothing and the run finish ``completed`` with no error. From
the outside this is indistinguishable from "the model had nothing to say": no
exception, no Sentry event, HTTP 200 with an empty body.

This helper makes those misconfigurations loud without changing the degrade
behaviour. The builder still skips the broken tool; it just additionally reports
*why* via ``log.error`` (captured as a Sentry event under the default
``LoggingIntegration``) plus an explicit ``sentry_sdk.capture_message`` carrying
a ``subsystem=runtime_tools`` tag, so the breakage surfaces in Sentry instead of
disappearing.

``sentry_sdk`` is imported optionally so the runtime stays importable and
unit-testable without it.
"""
from __future__ import annotations

import logging
from typing import Any

try:  # pragma: no cover - optional dep
    import sentry_sdk
except Exception:  # pragma: no cover - optional dep
    sentry_sdk = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

_SUBSYSTEM = "runtime_tools"


def _scoped_capture_message(message: str, where: str, level: str, tags: dict[str, Any]) -> None:
    if sentry_sdk is None:
        return
    try:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("subsystem", _SUBSYSTEM)
            scope.set_tag("where", where)
            for key, value in tags.items():
                scope.set_tag(key, str(value))
            sentry_sdk.capture_message(message, level=level)
    except Exception:  # noqa: BLE001 - reporting must never raise into the caller
        log.debug("runtime_tools: sentry message failed for where=%s", where)


def note(message: str, *, where: str, level: str = "error", **tags: Any) -> None:
    """Report a non-exception tool-assembly problem loudly (log + Sentry).

    ``where`` is a short stable identifier (e.g. ``"build_tools.zero_actions"``)
    used as a Sentry tag. ``level="error"`` emits a Sentry event; ``"warning"``
    stays a breadcrumb.
    """
    log_fn = log.error if level == "error" else log.warning
    log_fn("runtime_tools %s: %s", where, message)
    _scoped_capture_message(f"runtime_tools {where}: {message}", where, level, tags)


__all__ = ["note"]
