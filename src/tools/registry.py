"""Explicit, slug-based tool registry.

Every concrete tool service under ``src/tools/`` registers itself with the
``@register_tool(slug=..., name_fa=...)`` decorator placed on the class. The
``slug`` is the **stable identifier** the platform stores in the DB to bind a
tool action to its code; it no longer matters where the file lives. ``name_fa``
is the Persian display name shown to admins.

The main entry method is always ``run`` (enforced as abstract on
:class:`tools.base_tool.BaseToolService`), so the registry maps ``slug`` →
service class and the runtime simply calls ``.run()``.

``load_registry()`` eagerly imports every module under the ``tools`` package so
the decorators actually fire. It is idempotent and is wired into application
bootstrap. Discovery/runtime lookups also lazily trigger a load on a miss, so
tests and tooling that touch the registry before bootstrap still work.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

logger = logging.getLogger(__name__)


class UnknownToolSlug(KeyError):
    """Raised when a slug has no registered tool service."""


@dataclass(frozen=True)
class ToolRegistration:
    slug: str
    name_fa: str
    service_class: type
    module: str

    @property
    def class_name(self) -> str:
        return self.service_class.__name__


_REGISTRY: dict[str, ToolRegistration] = {}
_loaded = False


def register_tool(*, slug: str, name_fa: str):
    """Class decorator that registers a tool service under ``slug``.

    Raises at import time on an empty slug or a duplicate slug, so collisions
    surface as soon as the module is imported rather than silently at runtime.
    """
    normalized = (slug or "").strip()
    if not normalized:
        raise ValueError("register_tool requires a non-empty slug")

    def decorator(cls: type) -> type:
        existing = _REGISTRY.get(normalized)
        if existing is not None and existing.service_class is not cls:
            raise ValueError(
                f"Duplicate tool slug '{normalized}': already registered to "
                f"{existing.service_class.__module__}.{existing.class_name}"
            )
        cls.__tool_slug__ = normalized
        cls.__tool_name_fa__ = (name_fa or "").strip() or normalized
        _REGISTRY[normalized] = ToolRegistration(
            slug=normalized,
            name_fa=cls.__tool_name_fa__,
            service_class=cls,
            module=cls.__module__,
        )
        return cls

    return decorator


_SKIP_LEAVES = {"base_tool", "registry"}


def _iter_tool_module_names() -> set[str]:
    """Discover dotted module names for every ``*.py`` under the tools package.

    Walks the filesystem directly (rather than ``pkgutil``) so it works even
    though the tool sub-packages are namespace packages without ``__init__``.
    """
    import tools

    names: set[str] = set()
    for root in map(Path, tools.__path__):
        if not root.is_dir():
            continue
        for py_file in root.rglob("*.py"):
            leaf = py_file.stem
            if leaf.startswith("_") or leaf in _SKIP_LEAVES:
                continue
            relative = py_file.relative_to(root).with_suffix("")
            names.add("tools." + ".".join(relative.parts))
    return names


def load_registry() -> None:
    """Eagerly import every tool module so decorators register their classes.

    Idempotent: the filesystem walk runs only once per process.
    """
    global _loaded
    if _loaded:
        return

    for module_name in sorted(_iter_tool_module_names()):
        try:
            importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import tool module %s", module_name)

    _loaded = True
    logger.info("Tool registry loaded: %d tools", len(_REGISTRY))


def get_registration(slug: str) -> ToolRegistration:
    """Return the registration for ``slug`` (lazily loading on a miss)."""
    normalized = (slug or "").strip()
    registration = _REGISTRY.get(normalized)
    if registration is None and not _loaded:
        load_registry()
        registration = _REGISTRY.get(normalized)
    if registration is None:
        raise UnknownToolSlug(normalized)
    return registration


def get_service_class(slug: str) -> Type:
    """Return the tool service class registered under ``slug``."""
    return get_registration(slug).service_class


def has_slug(slug: str) -> bool:
    """Return whether ``slug`` is registered (lazily loading on a miss)."""
    normalized = (slug or "").strip()
    if normalized in _REGISTRY:
        return True
    if not _loaded:
        load_registry()
    return normalized in _REGISTRY


def list_registrations() -> list[dict[str, str]]:
    """Return all registered tools as plain dicts, sorted by slug."""
    if not _loaded:
        load_registry()
    return [
        {
            "slug": reg.slug,
            "name_fa": reg.name_fa,
            "class_name": reg.class_name,
            "module": reg.module,
        }
        for reg in sorted(_REGISTRY.values(), key=lambda r: r.slug)
    ]


__all__ = [
    "ToolRegistration",
    "UnknownToolSlug",
    "register_tool",
    "load_registry",
    "get_registration",
    "get_service_class",
    "has_slug",
    "list_registrations",
]
