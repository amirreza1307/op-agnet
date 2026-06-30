from __future__ import annotations

from pathlib import Path
from typing import Optional

from agno.skills.agent_skills import Skills
from agno.skills.loaders.local import LocalSkills

from api.errors import BadRequestError
from database.models.main.skill_package import SkillPackage
from setup.config import config
from setup.translator import trans


class SkillLoaderService:
    @staticmethod
    def list_available_skill_sources() -> list[dict[str, str]]:
        base_dir = config.skills_root_dir.resolve()
        items: list[dict[str, str]] = []
        if not base_dir.is_dir():
            return items

        for candidate in sorted(base_dir.iterdir()):
            if not candidate.is_dir():
                continue
            if candidate.name.startswith("_"):
                continue

            skill_file = candidate / "SKILL.md"
            if not skill_file.exists():
                continue

            items.append(
                {
                    "source_path": str(candidate.relative_to(base_dir)).replace("\\", "/"),
                    "display_name": candidate.name,
                    "has_skill_file": True,
                }
            )

        return items

    @staticmethod
    def resolve_source_path(source_path: str) -> Path:
        base_dir = config.skills_root_dir.resolve()
        requested = (source_path or "").strip()
        if not requested:
            raise BadRequestError(trans("errors.platform.admin.skill_source_path_required"))

        candidate_path = Path(requested)
        if candidate_path.is_absolute():
            candidate = candidate_path.resolve()
        else:
            candidate = (base_dir / requested).resolve()

        if base_dir not in {candidate, *candidate.parents}:
            raise BadRequestError(trans("errors.platform.admin.skill_source_path_outside_root", base_dir=base_dir))
        return candidate

    @classmethod
    def ensure_source_directory(cls, source_path: str) -> str:
        resolved = cls.resolve_source_path(source_path)
        resolved.mkdir(parents=True, exist_ok=True)
        return str(resolved)

    @classmethod
    def build_skills(cls, packages: list[SkillPackage]) -> Optional[Skills]:
        loaders = []
        for package in packages:
            loaders.append(LocalSkills(path=str(cls.resolve_source_path(package.source_path)), validate=False))
        if not loaders:
            return None
        return Skills(loaders=loaders)
