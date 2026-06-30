"""Path security helpers for MCP working_directory inputs."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from api.errors import BadRequestError
from setup.config import config
from setup.translator import trans


def resolve_mcp_working_directory(working_directory: Optional[str]) -> str:
    """Resolve and validate that the MCP working_directory stays inside ``mcp_root_dir``."""
    base_dir = config.mcp_root_dir
    requested = (working_directory or "").strip()
    if not requested:
        return str(base_dir)

    candidate_path = Path(requested)
    if candidate_path.is_absolute():
        candidate = candidate_path.resolve()
    else:
        candidate = (base_dir / requested).resolve()
    if base_dir not in {candidate, *candidate.parents}:
        raise BadRequestError(trans("errors.platform.admin.mcp_working_directory_outside_root", base_dir=base_dir))
    return str(candidate)


def ensure_mcp_working_directory(working_directory: Optional[str]) -> str:
    """Resolve, then create-on-disk the MCP working_directory."""
    resolved = Path(resolve_mcp_working_directory(working_directory))
    resolved.mkdir(parents=True, exist_ok=True)
    return str(resolved)
