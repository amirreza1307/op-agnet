"""CRUD + binding admin for Skill packages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from api.errors import ConflictError, NotFoundError
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.agent_node_skill_binding_repo import AgentNodeSkillBindingRepo
from database.repositories.main.skill_package_repo import SkillPackageRepo
from services.platform.admin._shared import normalize_payload
from services.platform.admin.mcp.skill_loader_service import SkillLoaderService
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.config import config
from setup.translator import trans


class SkillPackageAdmin:
    @staticmethod
    async def list_skills() -> list[Any]:
        return await SkillPackageRepo.get_all_active_skills()

    @staticmethod
    async def create_skill(payload: dict) -> Any:
        existing = await SkillPackageRepo.find_active_by_slug(payload["slug"])
        if existing:
            raise ConflictError(trans("errors.platform.admin.skill_slug_exists", slug=payload["slug"]))
        normalized_payload = dict(payload)
        normalized_payload["source_path"] = SkillPackageAdmin._normalize_skill_source_path(payload["source_path"])
        result = await SkillPackageRepo.create_return(normalize_payload("skill", normalized_payload))
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def update_skill(skill_id: int, payload: dict) -> Any:
        if "slug" in payload:
            existing = await SkillPackageRepo.find_active_by_slug(payload["slug"])
            if existing and existing.id != skill_id:
                raise ConflictError(trans("errors.platform.admin.skill_slug_exists", slug=payload["slug"]))
        if "source_path" in payload:
            payload["source_path"] = SkillPackageAdmin._normalize_skill_source_path(payload["source_path"])
        payload = normalize_payload("skill", payload)
        if payload:
            result = await SkillPackageRepo.update_by_id(skill_id, payload, return_=True)
        else:
            result = await SkillPackageRepo.find_active_by_id(skill_id)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def bind_skill(node_id: int, payload: dict) -> Any:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        skill = await SkillPackageRepo.find_active_by_id(payload["skill_package_id"])
        if node is None or skill is None:
            raise NotFoundError(trans("errors.platform.admin.node_and_skill_required"))
        result = await AgentNodeSkillBindingRepo.create_return(
            normalize_payload(
                "node_skill_binding",
                {
                    "node_id": node_id,
                    "skill_package_id": payload["skill_package_id"],
                    "priority": payload.get("priority", 0),
                    "is_enabled": payload.get("is_enabled", True),
                    "metadata_json": payload.get("metadata_json"),
                },
            )
        )
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def unbind_skill(binding_id: int) -> Any:
        result = await AgentNodeSkillBindingRepo.update_by_id(binding_id, {"is_enabled": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def deactivate_skill(skill_id: int) -> Any:
        skill = await SkillPackageRepo.find_active_by_id(skill_id)
        if skill is None:
            raise NotFoundError(trans("errors.platform.admin.skill_not_found", skill_id=skill_id))
        result = await SkillPackageRepo.update_by_id(skill_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    def _normalize_skill_source_path(source_path: str) -> str:
        resolved = SkillLoaderService.ensure_source_directory(source_path)
        base_dir = config.skills_root_dir.resolve()
        try:
            return str(Path(resolved).resolve().relative_to(base_dir))
        except ValueError:
            return resolved
