"""MCP payload validation and URL normalization."""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from api.errors import BadRequestError
from setup.translator import trans

from services.platform.admin.mcp.mcp_path_security import resolve_mcp_working_directory


def validate_mcp_payload(payload: dict) -> None:
    transport = payload.get("transport")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise BadRequestError(trans("errors.platform.admin.mcp_transport_invalid"))
    if transport == "stdio" and not payload.get("command"):
        raise BadRequestError(trans("errors.platform.admin.mcp_stdio_command_required"))
    if transport in {"sse", "streamable-http"} and not payload.get("url"):
        raise BadRequestError(trans("errors.platform.admin.mcp_http_url_required"))
    if transport == "stdio":
        resolve_mcp_working_directory(payload.get("working_directory"))


def normalize_remote_mcp_url(transport: Optional[str], url: Optional[str]) -> Optional[str]:
    raw_url = str(url or "").strip()
    if not raw_url or transport != "streamable-http":
        return raw_url or None

    parts = urlsplit(raw_url)
    path = parts.path or ""
    last_segment = path.rsplit("/", 1)[-1].lower()

    # Some MCP gateways redirect `/mcp` to `/mcp/`, and the current MCP client
    # can fail the POST initialize handshake when that redirect chain occurs.
    if path and not path.endswith("/") and last_segment == "mcp" and not parts.query and not parts.fragment:
        return urlunsplit(parts._replace(path=path + "/"))

    return raw_url
