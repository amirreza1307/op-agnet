from __future__ import annotations

import inspect
import shlex
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from api.errors import BadRequestError
from setup.config import config
from setup.translator import trans
from services.platform.runtime.agno.runtime_context import (
    build_mcp_runtime_arguments,
    build_runtime_env,
    build_runtime_session_state,
    build_runtime_transport_headers,
    get_runtime_session_state,
)
from services.platform.runtime.templating import render_header_template
from services.platform.runtime.tools.tool_name_sanitizer import (
    build_tool_description,
    sanitize_provider_tool_name,
    sanitize_tool_name_prefix,
)

try:
    from agno.tools.mcp import MCPTools
    from agno.tools.function import Function
    from agno.utils.mcp import prepare_command
    from agno.utils.mcp import get_entrypoint_for_tool
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception:  # pragma: no cover - optional until installed
    MCPTools = None
    Function = None
    get_entrypoint_for_tool = None
    prepare_command = None
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


# Legacy ``_SafeDict``/``str.format_map`` path is gone. Header templates now
# go through ``services.platform.runtime.templating.render_header_template``
# which uses a strict ``{{name}}`` regex with allow-listed lookup — no
# attribute traversal and no Python format-string CVEs.


if MCPTools is not None and Function is not None and get_entrypoint_for_tool is not None:
    class PlatformMCPTools(MCPTools):
        def __init__(self, *args, env_provider=None, **kwargs):
            self.env_provider = env_provider
            super().__init__(*args, **kwargs)

        async def build_tools(self) -> None:
            if self.session is None:
                raise ValueError("Session is not initialized")

            try:
                available_tools = await self.session.list_tools()  # type: ignore[attr-defined]

                self._check_tools_filters(
                    available_tools=[tool.name for tool in available_tools.tools],
                    include_tools=self.include_tools,
                    exclude_tools=self.exclude_tools,
                )

                filtered_tools = []
                for tool in available_tools.tools:
                    if self.exclude_tools and tool.name in self.exclude_tools:
                        continue
                    if self.include_tools is None or tool.name in self.include_tools:
                        filtered_tools.append(tool)

                prefix = ""
                if self.tool_name_prefix is not None:
                    prefix = sanitize_tool_name_prefix(self.tool_name_prefix, fallback="mcp") + "_"

                for tool in filtered_tools:
                    try:
                        entrypoint = get_entrypoint_for_tool(
                            tool=tool,
                            session=self.session,  # type: ignore[arg-type]
                            mcp_tools_instance=self,
                        )
                        wrapped_entrypoint = self._wrap_entrypoint(
                            entrypoint,
                            getattr(tool, "inputSchema", None),
                        )
                        tool_name = str(getattr(tool, "name", "") or "").strip()
                        tool_title = str(getattr(tool, "title", "") or "").strip()
                        provider_name = sanitize_provider_tool_name(
                            prefix + tool_name,
                            f"{prefix}{tool_title}" if tool_title else None,
                            fallback="mcp_tool",
                        )
                        description = build_tool_description(
                            getattr(tool, "description", None),
                            display_name=tool_name or None,
                            provider_name=provider_name,
                        )
                        function = Function(
                            name=provider_name,
                            description=description,
                            parameters=getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}},
                            entrypoint=wrapped_entrypoint,
                            skip_entrypoint_processing=True,
                        )
                        self.functions[function.name] = function
                    except Exception as exc:
                        raise RuntimeError(trans("errors.platform.runtime.mcp_tool_register_failed", tool_name=tool.name, error=exc)) from exc
            except (RuntimeError, BaseException):
                raise

        async def get_session_for_run(self, run_context=None, agent=None, team=None):
            if (
                self.transport != "stdio"
                or self.env_provider is None
                or run_context is None
                or stdio_client is None
                or ClientSession is None
            ):
                return await super().get_session_for_run(run_context=run_context, agent=agent, team=team)

            await self._cleanup_stale_sessions()
            run_id = run_context.run_id
            if run_id in self._run_sessions:
                session, _ = self._run_sessions[run_id]
                return session

            if self.server_params is None:
                raise ValueError("server_params must be provided when using stdio transport.")

            dynamic_env = self._call_env_provider(run_context=run_context, agent=agent, team=team)
            base_env = dict(getattr(self.server_params, "env", None) or {})
            server_params = StdioServerParameters(
                command=self.server_params.command,
                args=list(getattr(self.server_params, "args", []) or []),
                env={**base_env, **dynamic_env},
                cwd=getattr(self.server_params, "cwd", None),
            )
            context = stdio_client(server_params)  # type: ignore[arg-type]
            session_params = await context.__aenter__()  # type: ignore[attr-defined]
            read, write = session_params[0:2]
            session_context = ClientSession(
                read,
                write,
                read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
            )
            session = await session_context.__aenter__()  # type: ignore[attr-defined]
            await session.initialize()
            self._run_sessions[run_id] = (session, time.time())
            self._run_session_contexts[run_id] = (context, session_context)
            return session

        def _call_env_provider(self, run_context=None, agent=None, team=None) -> dict[str, str]:
            env_provider = getattr(self, "env_provider", None)
            if env_provider is None:
                return {}

            try:
                sig = inspect.signature(env_provider)
                call_kwargs: dict[str, Any] = {}
                param_names = set(sig.parameters.keys())
                if "run_context" in param_names:
                    call_kwargs["run_context"] = run_context
                if "agent" in param_names:
                    call_kwargs["agent"] = agent
                if "team" in param_names:
                    call_kwargs["team"] = team
                has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                if has_var_keyword:
                    return env_provider(run_context=run_context, agent=agent, team=team)
                if call_kwargs:
                    return env_provider(**call_kwargs)
                return env_provider()
            except Exception:
                return {}

        @staticmethod
        def _wrap_entrypoint(entrypoint, parameters):
            async def wrapped_entrypoint(run_context=None, agent=None, team=None, **kwargs):
                session_state = build_runtime_session_state(
                    get_runtime_session_state(run_context=run_context, agent=agent, team=team),
                    session_id=getattr(run_context, "session_id", None) or getattr(agent, "session_id", None),
                )
                injected_arguments = build_mcp_runtime_arguments(parameters, session_state)
                for key, value in injected_arguments.items():
                    kwargs.setdefault(key, value)
                return await entrypoint(run_context=run_context, agent=agent, team=team, **kwargs)

            return wrapped_entrypoint
else:  # pragma: no cover - optional import guard
    PlatformMCPTools = None


class McpBindingFactory:
    @staticmethod
    def create(server, binding):
        if PlatformMCPTools is None:
            raise RuntimeError(trans("errors.platform.runtime.mcp_not_installed"))

        kwargs: dict[str, Any] = {
            "transport": server.transport,
            "timeout_seconds": server.timeout_seconds or config.MCP_DEFAULT_TIMEOUT_SECONDS,
            "include_tools": server.include_tools_json,
            "exclude_tools": server.exclude_tools_json,
            "refresh_connection": server.refresh_connection,
            "tool_name_prefix": sanitize_tool_name_prefix(
                server.tool_name_prefix,
                getattr(server, "slug", None),
                getattr(server, "name", None),
                fallback="mcp",
            ),
        }

        env = server.env_json or {}
        if server.transport == "stdio":
            working_directory = McpBindingFactory._resolve_working_directory(server)
            if StdioServerParameters is not None and prepare_command is not None:
                command_parts = McpBindingFactory._split_stdio_command(server.command)
                kwargs["server_params"] = StdioServerParameters(
                    command=command_parts[0],
                    args=command_parts[1:],
                    env=env,
                    cwd=str(working_directory),
                )
                kwargs["env_provider"] = McpBindingFactory._build_env_provider()
            else:
                kwargs["command"] = server.command
                kwargs["env"] = env
        else:
            kwargs["url"] = server.url
            template_headers = binding.header_template_json or server.headers_json or {}
            kwargs["header_provider"] = McpBindingFactory._build_header_provider(template_headers)

        return PlatformMCPTools(**kwargs)

    @staticmethod
    def _split_stdio_command(command: str) -> list[str]:
        raw_command = (command or "").strip()
        if not raw_command:
            raise BadRequestError(trans("errors.platform.runtime.mcp_stdio_command_required"))

        try:
            parsed_parts = shlex.split(raw_command, posix=False)
        except ValueError as exc:
            raise BadRequestError(trans("errors.platform.runtime.mcp_invalid_command", error=exc)) from exc

        if not parsed_parts:
            raise BadRequestError(trans("errors.platform.runtime.mcp_stdio_command_required"))

        executable = parsed_parts[0].strip("\"'")
        if Path(executable).is_absolute() and Path(executable).exists():
            return [executable, *parsed_parts[1:]]

        if prepare_command is None:
            return parsed_parts

        return prepare_command(raw_command)

    @staticmethod
    def _build_header_provider(template_headers: dict[str, Any]):
        def header_provider(run_context=None, agent=None, team=None):
            session_state = build_runtime_session_state(
                get_runtime_session_state(run_context=run_context, agent=agent, team=team),
                session_id=getattr(run_context, "session_id", None) or getattr(agent, "session_id", None),
            )

            resolved: dict[str, Any] = build_runtime_transport_headers(session_state)
            for key, value in template_headers.items():
                if isinstance(value, str):
                    resolved[key] = render_header_template(value, session_state)
                else:
                    resolved[key] = value
            return resolved

        return header_provider

    @staticmethod
    def _build_env_provider():
        def env_provider(run_context=None, agent=None, team=None):
            session_state = build_runtime_session_state(
                get_runtime_session_state(run_context=run_context, agent=agent, team=team),
                session_id=getattr(run_context, "session_id", None) or getattr(agent, "session_id", None),
            )
            return build_runtime_env(session_state)

        return env_provider

    @staticmethod
    def _resolve_working_directory(server) -> Path:
        base_dir = config.mcp_root_dir
        requested = (server.working_directory or "").strip()
        if not requested:
            return base_dir

        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = (base_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if base_dir not in {candidate, *candidate.parents}:
            raise BadRequestError(trans("errors.platform.runtime.mcp_working_directory_outside_root", base_dir=base_dir))

        return candidate

