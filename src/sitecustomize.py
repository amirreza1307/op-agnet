from __future__ import annotations

import sys
from pathlib import Path


def _prefer_local_basalam_namespace() -> None:
    local_basalam = Path(__file__).resolve().parent / "basalam"
    if not local_basalam.exists():
        return

    loaded = sys.modules.get("basalam")
    if loaded is None:
        return

    package_path = getattr(loaded, "__path__", None)
    if package_path is None:
        return

    local_path = str(local_basalam)
    if local_path in package_path:
        return

    try:
        package_path.insert(0, local_path)
    except AttributeError:
        loaded.__path__ = [local_path, *list(package_path)]


_prefer_local_basalam_namespace()
