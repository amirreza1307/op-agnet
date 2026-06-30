"""CRUD admin operations for Tool / Action / binding entities."""
from __future__ import annotations

from typing import Any, Optional

from api.errors import BadRequestError, ConflictError, NotFoundError
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.agent_node_tool_binding_repo import AgentNodeToolBindingRepo
from database.repositories.main.tool_action_binding_repo import ToolActionBindingRepo
from database.repositories.main.tool_action_repo import ToolActionRepo
from database.repositories.main.tool_repo import ToolRepo
from services.platform.admin._shared import normalize_payload
from services.platform.admin.tools.tool_actions_resolver import (
    resolve_tool_actions_payload,
)
from services.platform.admin.tools.tool_cache_service import ToolCacheService
from services.platform.admin.tools.tool_schemas import ToolUpdateSchema
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans
from tools.registry import has_slug


class ToolAdmin:
    @staticmethod
    async def list_tools() -> list[Any]:
        return await ToolCacheService.list_tools()

    @staticmethod
    async def list_actions() -> list[Any]:
        return await ToolActionRepo.get_all_active_actions()

    @staticmethod
    async def create_tool(payload: dict) -> Any:
        existing = await ToolRepo.find_active_by_slug(payload["slug"])
        if existing:
            raise ConflictError(trans("errors.platform.admin.tool_slug_exists", slug=payload["slug"]))

        actions_payload = await resolve_tool_actions_payload(payload)
        tool_payload = {
            "slug": payload["slug"],
            "name": payload["name"],
            "description": payload["description"],
            "progress_label": payload.get("progress_label"),
            "progress_visual_type": payload.get("progress_visual_type"),
            "progress_visual_value": payload.get("progress_visual_value"),
            "tool_type": payload["tool_type"],
            "parameters": payload.get("parameters", []),
            "required_tool_ids": payload.get("required_tool_ids", []),
            "show_result": payload.get("show_result", False),
            "action_only_name": payload.get("action_only_name"),
            "action_only_description": payload.get("action_only_description"),
            "rule_method": payload.get("rule_method"),
            "is_active": payload.get("is_active", True),
            "is_public": payload.get("is_public", False),
            "public_name": payload.get("public_name"),
            "user_types": [],
            "agent_id": None,
            "api_url": payload.get("api_url"),
            "api_method": payload.get("api_method", "GET"),
            "api_headers": payload.get("api_headers"),
            "api_body_template": payload.get("api_body_template"),
            "metadata_json": payload.get("metadata_json"),
            "created_by": payload.get("created_by"),
        }
        tool = await ToolRepo.create_return(normalize_payload("tool", tool_payload))
        await ToolAdmin._replace_tool_actions(tool.id, actions_payload)
        await PlatformCacheManager.refresh()
        return tool

    @staticmethod
    async def update_tool(tool_id: int, payload: dict) -> Any:
        current_tool = await ToolRepo.find_active_by_id(tool_id)
        if current_tool is None:
            raise NotFoundError(trans("errors.platform.admin.tool_not_found", tool_id=tool_id))
        if "slug" in payload:
            existing = await ToolRepo.find_active_by_slug(payload["slug"])
            if existing and existing.id != tool_id:
                raise ConflictError(trans("errors.platform.admin.tool_slug_exists", slug=payload["slug"]))

        actions_payload = await resolve_tool_actions_payload(payload)

        # Filter caller-supplied fields through the pydantic allow-list schema —
        # unknown keys are rejected (extra="forbid") and only the explicitly-set
        # subset is forwarded to the repository.
        admin_only_payload = {
            key: value
            for key, value in payload.items()
            if key in ToolUpdateSchema.model_fields
        }
        try:
            schema = ToolUpdateSchema.model_validate(admin_only_payload)
        except Exception as exc:
            raise BadRequestError(str(exc))
        update_payload = schema.model_dump(exclude_unset=True)

        update_payload = normalize_payload("tool", update_payload)
        if update_payload:
            tool = await ToolRepo.update_by_id(tool_id, update_payload, return_=True)
        else:
            tool = current_tool

        if actions_payload is not None:
            await ToolAdmin._replace_tool_actions(tool_id, actions_payload)

        await PlatformCacheManager.refresh()
        return tool

    @staticmethod
    async def deactivate_tool(tool_id: int) -> Any:
        tool = await ToolRepo.find_active_by_id(tool_id)
        if tool is None:
            raise NotFoundError(trans("errors.platform.admin.tool_not_found", tool_id=tool_id))
        result = await ToolRepo.update_by_id(tool_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def create_action(payload: dict) -> Any:
        if not has_slug(payload["slug"]):
            raise BadRequestError(trans("errors.platform.admin.unknown_tool_slug", slug=payload["slug"]))
        existing = await ToolActionRepo.find_active_by_slug(payload["slug"])
        if existing:
            raise ConflictError(trans("errors.platform.admin.action_slug_exists", slug=payload["slug"]))
        result = await ToolActionRepo.create_return(
            normalize_payload(
                "action",
                {
                    "slug": payload["slug"],
                    "name": payload["name"],
                    "description": payload.get("description", ""),
                    "is_active": payload.get("is_active", True),
                    "metadata_json": payload.get("metadata_json"),
                },
            )
        )
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def update_action(action_id: int, payload: dict) -> Any:
        if "slug" in payload:
            existing = await ToolActionRepo.find_active_by_slug(payload["slug"])
            if existing and existing.id != action_id:
                raise ConflictError(trans("errors.platform.admin.action_slug_exists", slug=payload["slug"]))
        payload = normalize_payload("action", payload)
        if payload:
            result = await ToolActionRepo.update_by_id(action_id, payload, return_=True)
        else:
            result = await ToolActionRepo.find_active_by_id(action_id)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def deactivate_action(action_id: int) -> Any:
        action = await ToolActionRepo.find_active_by_id(action_id)
        if action is None:
            raise NotFoundError(trans("errors.platform.admin.action_not_found", action_id=action_id))
        result = await ToolActionRepo.update_by_id(action_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def bind_tool(node_id: int, payload: dict) -> Any:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        tool = await ToolRepo.find_active_by_id(payload["tool_id"])
        if node is None or tool is None:
            raise NotFoundError(trans("errors.platform.admin.node_and_tool_required"))
        result = await AgentNodeToolBindingRepo.create_return(
            normalize_payload(
                "node_tool_binding",
                {
                    "node_id": node_id,
                    "tool_id": payload["tool_id"],
                    "priority": payload.get("priority", 0),
                    "is_enabled": payload.get("is_enabled", True),
                    "binding_mode": payload.get("binding_mode"),
                    "metadata_json": payload.get("metadata_json"),
                },
            )
        )
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def unbind_tool(binding_id: int) -> Any:
        bindings = await AgentNodeToolBindingRepo.get_all_active_bindings()
        binding = next((item for item in bindings if item.id == binding_id), None)
        if binding is None:
            raise NotFoundError(trans("errors.platform.admin.tool_binding_not_found", binding_id=binding_id))
        result = await AgentNodeToolBindingRepo.update_by_id(binding_id, {"is_enabled": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def bind_action(tool_id: int, payload: dict) -> Any:
        tool = await ToolRepo.find_active_by_id(tool_id)
        action = await ToolActionRepo.find_active_by_id(payload["action_id"])
        if tool is None or action is None:
            raise NotFoundError(trans("errors.platform.admin.tool_and_action_required"))
        result = await ToolActionBindingRepo.create_return(
            normalize_payload(
                "tool_action_binding",
                {
                    "tool_id": tool_id,
                    "action_id": payload["action_id"],
                    "constructor_params": payload.get("constructor_params", {}),
                    "response_title": payload.get("response_title"),
                    "priority": payload.get("priority", 0),
                    "is_enabled": payload.get("is_enabled", True),
                    "metadata_json": payload.get("metadata_json"),
                },
            )
        )
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def unbind_action(binding_id: int) -> Any:
        result = await ToolActionBindingRepo.update_by_id(binding_id, {"is_enabled": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def _replace_tool_actions(tool_id: int, actions_payload: Optional[list[dict]]) -> None:
        if actions_payload is None:
            return

        existing_bindings = await ToolActionBindingRepo.get_bindings_by_tool_id(tool_id)
        for binding in existing_bindings:
            await ToolActionBindingRepo.update_by_id(binding.id, {"is_enabled": False}, return_=False)
        legacy_actions = await ToolActionRepo.get_actions_by_tool_id(tool_id)
        for legacy_action in legacy_actions:
            await ToolActionRepo.update_by_id(legacy_action.id, {"is_active": False}, return_=False)

        for action_payload in actions_payload:
            await ToolAdmin._create_inline_action_binding(tool_id, action_payload)

    @staticmethod
    async def _create_inline_action_binding(tool_id: int, action_payload: dict) -> Any:
        action_id = action_payload.get("action_id")
        if action_id is not None:
            action = await ToolActionRepo.find_active_by_id(action_id)
            if action is None:
                raise NotFoundError(trans("errors.platform.admin.action_not_found", action_id=action_id))
        if action_id is None:
            action_slug = action_payload.get("slug")
            if not action_slug:
                raise BadRequestError(trans("errors.platform.admin.inline_action_requires_slug"))
            if not has_slug(action_slug):
                raise BadRequestError(trans("errors.platform.admin.unknown_tool_slug", slug=action_slug))

            existing = await ToolActionRepo.find_active_by_slug(action_slug)
            if existing:
                action_id = existing.id
            else:
                created = await ToolActionRepo.create_return(
                    normalize_payload(
                        "action",
                        {
                            "slug": action_slug,
                            "name": action_payload.get("name") or action_slug,
                            "description": action_payload.get("description", ""),
                            "is_active": action_payload.get("is_active", True),
                        },
                    )
                )
                action_id = created.id

        return await ToolActionBindingRepo.create_return(
            normalize_payload(
                "tool_action_binding",
                {
                    "tool_id": tool_id,
                    "action_id": action_id,
                    "constructor_params": action_payload.get("constructor_params", {}),
                    "response_title": action_payload.get("response_title"),
                    "priority": action_payload.get("priority", 0),
                    "is_enabled": action_payload.get("is_active", True),
                },
            )
        )
