"""Node runtime builder (Phases 2 + 8).

Decomposed responsibilities:
  * ``_resolve_instructions``    — composes instruction list.
  * ``_resolve_tools``           — tools + skills.
  * ``_resolve_child_node_tools``— child node bridge tools (no ``exec``).
  * ``_compose_runtime_kwargs``  — final Agno ``Agent`` kwargs.
  * ``build``                    — orchestrate + return :class:`BuiltNodeRuntime`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

from agno.agent import Agent
from pydantic import BaseModel

from api.errors import BadRequestError, ConflictError
from setup.config import config
from setup.translator import trans
from services.platform.admin.mcp.skill_loader_service import SkillLoaderService
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from services.platform.runtime.agno.agno_runtime import (
    build_model,
    get_agno_db,
    get_agno_memory_manager,
)
from services.platform.runtime.mcp.mcp_binding_factory import McpBindingFactory
from services.platform.runtime.tools.agno_function_builder import (
    ToolParam,
    ToolSpec,
    build_agno_function,
)
from services.platform.runtime.tools.dynamic_tool_factory import DynamicToolFactory
from services.platform.runtime.tools.dynamic_tool_helpers import (
    _resolve_runtime_target,
)
from services.platform.runtime.tools.parameter_resolver import (
    to_snake_case as _to_snake_case,
)
from services.platform.runtime.tools.tool_name_sanitizer import (
    build_tool_description,
    sanitize_provider_tool_name,
)
from services.platform.runtime.nodes._sentry import note as _report_tool_assembly

logger = logging.getLogger(__name__)


__all__ = ["NodeRuntimeBuilder", "BuiltNodeRuntime"]


@dataclass
class BuiltNodeRuntime:
    runtime: Any  # ``AgentRuntime`` Protocol (Agno Agent in practice)
    forced_output_schema: Optional[type[BaseModel]] = None
    forced_structured_outputs: Optional[bool] = None


class NodeRuntimeBuilder:
    @classmethod
    async def build(
        cls,
        *,
        node,
        session_state: dict,
        edge=None,
        depth: int = 0,
        active_path: Optional[set[int]] = None,
        extra_instructions: Optional[List[str]] = None,
    ) -> Any:
        """Build a runtime for ``node``.

        For backward compatibility this method returns the *runtime target*
        (``Agent``) directly with the forced-output attributes still attached
        via ``setattr``. New callers should use :meth:`build_runtime` which
        returns :class:`BuiltNodeRuntime` and avoids the backchannel.
        """
        built = await cls.build_runtime(
            node=node,
            session_state=session_state,
            edge=edge,
            depth=depth,
            active_path=active_path,
            extra_instructions=extra_instructions,
        )
        # Back-compat shim until all callers move to ``build_runtime``.
        if built.forced_output_schema is not None:
            setattr(built.runtime, "_platform_forced_output_schema", built.forced_output_schema)
        if built.forced_structured_outputs is not None:
            setattr(
                built.runtime,
                "_platform_forced_structured_outputs",
                built.forced_structured_outputs,
            )
        return built.runtime

    @classmethod
    async def build_runtime(
        cls,
        *,
        node,
        session_state: dict,
        edge=None,
        depth: int = 0,
        active_path: Optional[set[int]] = None,
        extra_instructions: Optional[List[str]] = None,
    ) -> BuiltNodeRuntime:
        if depth > config.PLATFORM_MAX_GRAPH_DEPTH:
            raise BadRequestError(trans("errors.platform.runtime.graph_depth_exceeded", limit=config.PLATFORM_MAX_GRAPH_DEPTH))

        node_session_state = dict(session_state or {})

        if active_path is None:
            active_path = set()
        if node.id in active_path:
            raise ConflictError(trans("errors.platform.runtime.cycle_while_materializing", node_id=node.id))
        next_active_path = frozenset(active_path | {node.id})

        output_config: dict[str, Any] = {}
        instructions = cls._resolve_instructions(node, edge, output_config, extra_instructions)
        description = cls._compose_agno_description(node.id, edge=edge)
        tools, skill_snippet = cls._resolve_tools(node.id)
        if skill_snippet:
            instructions.append(skill_snippet)
        tools.extend(cls._build_mcp_tools(node.id))
        tools.extend(
            cls._resolve_child_node_tools(
                parent_node_id=node.id,
                depth=depth,
                active_path=next_active_path,
            )
        )

        runtime_config = cls._get_runtime_config(node.id)
        runtime_config.update(output_config.get("runtime_overrides", {}))

        common_kwargs = cls._compose_runtime_kwargs(
            node=node,
            instructions=instructions,
            description=description,
            tools=tools,
            session_state=node_session_state,
            runtime_config=runtime_config,
            output_config=output_config,
            is_parent=edge is None,
        )

        runtime_target = Agent(
            structured_outputs=runtime_config.get("structured_outputs"),
            use_json_mode=runtime_config.get("use_json_mode", False),
            **common_kwargs,
        )
        if hasattr(runtime_target, "structured_outputs"):
            runtime_target.structured_outputs = runtime_config.get("structured_outputs")

        return BuiltNodeRuntime(
            runtime=runtime_target,
            forced_output_schema=output_config.get("forced_output_schema"),
            forced_structured_outputs=output_config.get("forced_structured_outputs"),
        )

    # ----- decomposed helpers -----------------------------------------------

    @classmethod
    def _resolve_instructions(
        cls,
        node,
        edge,
        output_config: dict[str, Any],
        extra_instructions: Optional[List[str]],
    ) -> list[str]:
        instructions = cls._compose_instructions(edge=edge)
        instructions.extend(output_config.get("instructions", []))
        if extra_instructions:
            instructions.extend([item for item in extra_instructions if item])
        return instructions

    @classmethod
    def _resolve_tools(cls, node_id: int) -> tuple[list[Any], Optional[str]]:
        tools = cls._build_tools(node_id)
        skills = cls._build_skills(node_id)
        snippet: Optional[str] = None
        if skills is not None:
            snippet_text = skills.get_system_prompt_snippet().strip()
            snippet = snippet_text or None
            tools.extend(skills.get_tools())
        return tools, snippet

    @classmethod
    def _resolve_child_node_tools(
        cls,
        *,
        parent_node_id: int,
        depth: int,
        active_path: frozenset[int],
    ) -> list[Any]:
        child_edges = PlatformCacheManager.get_children_edges(parent_node_id)
        if not child_edges:
            return []
        tools: list[Any] = []
        for child_edge in child_edges:
            child_node = PlatformCacheManager.get_node_by_id(child_edge.child_node_id)
            if child_node is None:
                logger.debug(
                    "child_node_missing_in_cache parent=%s child_id=%s",
                    parent_node_id,
                    child_edge.child_node_id,
                )
                continue
            tool = cls._make_child_node_tool(
                parent_node_id=parent_node_id,
                child_edge=child_edge,
                child_node=child_node,
                depth=depth,
                active_path=active_path,
            )
            if tool is not None:
                tools.append(tool)
        return tools

    @classmethod
    def _compose_runtime_kwargs(
        cls,
        *,
        node,
        instructions: list[str],
        description: str,
        tools: list[Any],
        session_state: dict[str, Any],
        runtime_config: dict[str, Any],
        output_config: dict[str, Any],
        is_parent: bool = False,
    ) -> dict[str, Any]:
        session_table = (node.session_table or "").strip() or None
        kwargs: dict[str, Any] = {
            "id": node.slug,
            "name": node.name,
            "instructions": instructions,
            "model": build_model(
                model_id=node.model_id,
                model_provider=getattr(node, "model_provider", None),
                model_api_key=getattr(node, "model_api_key", None),
                model_base_url=getattr(node, "model_base_url", None),
            ),
            "db": get_agno_db(session_table),
            "session_state": session_state,
            "add_session_state_to_context": False,
            "add_history_to_context": runtime_config.get("add_history_to_context", True),
            "num_history_runs": runtime_config.get("num_history_runs", config.PLATFORM_DEFAULT_HISTORY_RUNS),
            "cache_session": runtime_config.get("cache_session", True),
            "debug_mode": runtime_config.get("debug_mode", config.DEBUG),
            "telemetry": False,
            "tools": tools,
            "tool_call_limit": runtime_config.get("tool_call_limit", config.PLATFORM_DEFAULT_TOOL_CALL_LIMIT),
            "tool_choice": runtime_config.get("tool_choice"),
            "reasoning": runtime_config.get("reasoning", False),
            "reasoning_min_steps": runtime_config.get("reasoning_min_steps", 1),
            "reasoning_max_steps": runtime_config.get("reasoning_max_steps", 10),
            "read_chat_history": runtime_config.get("read_chat_history", False),
            "output_schema": runtime_config.get("output_schema"),
            "stream_events": runtime_config.get("stream_events"),
            "enable_session_summaries": runtime_config.get("enable_session_summaries", False),
            "update_memory_on_run": runtime_config.get("update_memory_on_run", False),
            "enable_agentic_memory": runtime_config.get("enable_agentic_memory", False),
            "enable_agentic_state": runtime_config.get("enable_agentic_state", False),
            "markdown": False,
            "pre_hooks": None,
            "post_hooks": None,
        }
        # Memory is a parent-only concern. Two mutually-exclusive modes are
        # selectable from runtime_config:
        #   * update_memory_on_run — manager runs after every response (reliable)
        #   * enable_agentic_memory — agent decides via tools when to store/recall
        # Both default to off, and both drive the same cheap-model memory manager.
        # Agno gives enable_agentic_memory precedence, so if a node mistakenly
        # enables both we force update_memory_on_run off to avoid ambiguity.
        if is_parent and kwargs["enable_agentic_memory"]:
            kwargs["update_memory_on_run"] = False
        if is_parent and (kwargs["update_memory_on_run"] or kwargs["enable_agentic_memory"]):
            memory_manager = get_agno_memory_manager(session_table)
            if memory_manager is not None:
                kwargs["memory_manager"] = memory_manager
        else:
            # Child nodes (and parents with memory off) never carry memory flags.
            kwargs["update_memory_on_run"] = False
            kwargs["enable_agentic_memory"] = False

        expected_output = output_config.get("expected_output")
        if expected_output:
            kwargs["expected_output"] = expected_output
        if description:
            kwargs["description"] = description
        return kwargs

    # ----- specialized builders ---------------------------------------------

    @staticmethod
    def _compose_agno_description(node_id: int, edge=None) -> str:
        node = PlatformCacheManager.get_node_by_id(node_id)
        parts: list[str] = []
        if node and node.system_prompt:
            parts.append(node.system_prompt.strip())
        if edge and node and node.description:
            parts.append(node.description.strip())
        return "\n\n".join(part for part in parts if part)

    @staticmethod
    def _compose_instructions(edge=None) -> list[str]:
        instructions: list[str] = []
        if edge and edge.member_instructions_json:
            instructions.extend([item for item in edge.member_instructions_json if item])
        return instructions

    @staticmethod
    def _build_tools(node_id: int) -> list[Any]:
        tools: list[Any] = []
        for binding in PlatformCacheManager.get_tool_bindings(node_id):
            tool_record = PlatformCacheManager.tools_by_id.get(binding.tool_id)
            if tool_record is None:
                continue
            actions = PlatformCacheManager.actions_by_tool_id.get(tool_record.id, [])
            # A ``script`` tool with zero actions is a misconfiguration, not a
            # no-op: it still builds into a callable function the model can
            # invoke, but every call returns an empty string, so the agent
            # answers with nothing and the run finishes ``completed`` with no
            # error (HTTP 200, empty body — indistinguishable from "nothing to
            # say"). This is exactly what happens when an action binding exists
            # but is left ``is_enabled=False``. Skip the hollow tool so the model
            # never sees it, and report loudly (log.error + Sentry) so the
            # broken binding surfaces instead of silently eating the answer.
            # ``api`` tools legitimately have no actions and are left untouched.
            if getattr(tool_record, "tool_type", None) == "script" and not actions:
                _report_tool_assembly(
                    "script tool has no enabled actions — skipped (check "
                    "tool_action_bindings.is_enabled)",
                    where="build_tools.zero_actions",
                    level="error",
                    node_id=node_id,
                    tool_id=getattr(tool_record, "id", None),
                    tool_slug=getattr(tool_record, "slug", None)
                    or getattr(tool_record, "name", None),
                )
                continue
            try:
                tools.append(
                    DynamicToolFactory.create_tool(
                        tool_record,
                        actions,
                        force_direct_response=False,
                    )
                )
            except ImportError as exc:
                logger.warning(
                    "tool_skip_import_error tool=%s id=%s node=%s error=%s",
                    getattr(tool_record, "slug", None) or getattr(tool_record, "name", None),
                    getattr(tool_record, "id", None),
                    node_id,
                    exc,
                )
        return tools

    @staticmethod
    def _build_mcp_tools(node_id: int) -> list[Any]:
        tools: list[Any] = []
        for binding in PlatformCacheManager.get_mcp_bindings(node_id):
            server = PlatformCacheManager.mcp_servers_by_id.get(binding.mcp_server_id)
            if server is None:
                continue
            tools.append(McpBindingFactory.create(server, binding))
        return tools

    @staticmethod
    def _build_skills(node_id: int):
        packages = []
        for binding in PlatformCacheManager.get_skill_bindings(node_id):
            skill = PlatformCacheManager.skills_by_id.get(binding.skill_package_id)
            if skill is not None:
                packages.append(skill)
        return SkillLoaderService.build_skills(packages)

    @staticmethod
    def _get_runtime_config(node_id: int) -> dict[str, Any]:
        node = PlatformCacheManager.get_node_by_id(node_id)
        if node is None or node.runtime_config_json is None:
            return {}
        return dict(node.runtime_config_json)

    @staticmethod
    def _get_child_node_parameters(child_node) -> list[dict[str, Any]]:
        metadata = getattr(child_node, "metadata_json", None) or {}
        if not isinstance(metadata, dict):
            return []
        raw_params = metadata.get("parameters")
        if not isinstance(raw_params, list):
            return []
        return [entry for entry in raw_params if isinstance(entry, dict) and entry.get("name")]

    @classmethod
    def _make_child_node_tool(
        cls,
        *,
        parent_node_id: int,
        child_edge,
        child_node,
        depth: int,
        active_path: frozenset[int],
    ):
        provider_name = sanitize_provider_tool_name(
            getattr(child_node, "slug", None),
            getattr(child_node, "name", None),
            f"child_node_{getattr(child_node, 'id', '')}",
        )

        description_body = cls._compose_agno_description(child_node.id, edge=child_edge)
        edge_instructions = cls._compose_instructions(edge=child_edge)
        if edge_instructions:
            description_body = "\n\n".join(
                part for part in [description_body, *edge_instructions] if part
            )
        tool_description = build_tool_description(
            description_body,
            display_name=getattr(child_node, "name", None),
            provider_name=provider_name,
        )

        node_parameters = cls._get_child_node_parameters(child_node)
        tool_params: list[ToolParam] = [ToolParam(name="message", type="str", default="")]
        seen: set[str] = {"message"}
        for entry in node_parameters:
            name = str(entry.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            tool_params.append(
                ToolParam(
                    name=name,
                    type=str(entry.get("type", "str")),
                    default=entry.get("default"),
                    required=bool(entry.get("required", False)),
                    description=entry.get("description"),
                )
            )

        canonical_param_names = {_to_snake_case(name) for name in seen if name != "message"}

        entrypoint = _ChildNodeEntrypoint(
            child_node_id=child_node.id,
            child_edge=child_edge,
            depth=depth + 1,
            active_path=active_path,
            canonical_param_names=canonical_param_names,
        )

        spec = ToolSpec(
            name=provider_name,
            description=tool_description,
            parameters=tool_params,
            entrypoint=entrypoint,
            show_result=False,
            stop_after_tool_call=False,
        )
        return build_agno_function(spec)


class _ChildNodeEntrypoint:
    """Runs a child node as a tool. Replaces the legacy ``exec``-built closure."""

    def __init__(
        self,
        *,
        child_node_id: int,
        child_edge,
        depth: int,
        active_path: frozenset[int],
        canonical_param_names: set[str],
    ) -> None:
        self.child_node_id = child_node_id
        self.child_edge = child_edge
        self.depth = depth
        self.active_path = active_path
        self.canonical_param_names = canonical_param_names

    async def __call__(
        self,
        kwargs: dict[str, Any],
        *,
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
    ) -> str:
        runtime_target = _resolve_runtime_target(agent, team, run_context, kwargs)
        session_state = dict(getattr(runtime_target, "session_state", {}) or {})

        provided_params: dict[str, Any] = {}
        for canonical in self.canonical_param_names:
            value = kwargs.get(canonical)
            if value is None:
                # Try camelCase alias.
                parts = canonical.split("_")
                camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
                value = kwargs.get(camel)
            if value is not None:
                provided_params[canonical] = value

        extra_instructions = [f"{name}: {value}" for name, value in provided_params.items()]
        message_value = kwargs.get("message") or ""

        fresh_child_node = PlatformCacheManager.get_node_by_id(self.child_node_id)
        if fresh_child_node is None:
            raise RuntimeError(trans("errors.platform.runtime.child_node_unavailable", child_node_id=self.child_node_id))

        child_runtime = await NodeRuntimeBuilder.build(
            node=fresh_child_node,
            session_state=session_state,
            edge=self.child_edge,
            depth=self.depth,
            active_path=set(self.active_path),
            extra_instructions=extra_instructions,
        )

        run_response = await child_runtime.arun(
            input=message_value,
            user_id=session_state.get("principal_id"),
            session_id=getattr(runtime_target, "session_id", None),
            session_state=session_state,
            stream=False,
        )

        content = getattr(run_response, "content", None)
        if content is None:
            return ""
        return content if isinstance(content, str) else str(content)
