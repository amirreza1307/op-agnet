from typing import Optional

from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.admin_request_models import (
    McpServerCreateRequestModel,
    McpServerTestRequestModel,
    McpServerUpdateRequestModel,
    SkillPackageCreateRequestModel,
    SkillPackageUpdateRequestModel,
    SkillPathValidationRequestModel,
)
from api.serializers import serialize_response_value
from services.platform.admin.queries.admin_query_service import AdminQueryService
from services.platform.admin.mcp.mcp_admin_service import MCPAdminService
from services.platform.admin.mcp.skill_loader_service import SkillLoaderService


class ResourceController(ControllerAbstract):

    # â”€â”€â”€ MCP Servers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def create_mcp_server(self, request_model: McpServerCreateRequestModel):
        return serialize_response_value(
            await MCPAdminService.create_mcp_server(
                request_model.model_dump(exclude_none=True)
            )
        )

    async def list_mcp_servers(self, include_inactive: bool = False, search: str | None = None):
        return await AdminQueryService.list_mcp_servers(
            include_inactive=include_inactive, search=search
        )

    async def list_local_mcp_sources(self):
        return MCPAdminService.list_local_mcp_sources()

    async def mcp_server_detail(self, server_id: int):
        return await AdminQueryService.get_mcp_server_detail(server_id)

    async def test_mcp_server(self, server_id: int, request_model: Optional[McpServerTestRequestModel]):
        payload = (
            request_model.model_dump(exclude_none=True) if request_model is not None else {}
        )
        return await AdminQueryService.test_mcp_server(server_id, payload)

    async def update_mcp_server(self, server_id: int, request_model: McpServerUpdateRequestModel):
        return serialize_response_value(
            await MCPAdminService.update_mcp_server(
                server_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def deactivate_mcp_server(self, server_id: int):
        return serialize_response_value(
            await MCPAdminService.deactivate_mcp_server(server_id)
        )

    # â”€â”€â”€ Skills â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def list_skills(self, include_inactive: bool = False, search: str | None = None):
        return await AdminQueryService.list_skills(
            include_inactive=include_inactive, search=search
        )

    async def list_skill_sources(self):
        return {"items": SkillLoaderService.list_available_skill_sources()}

    async def skill_detail(self, skill_id: int):
        return await AdminQueryService.get_skill_detail(skill_id)

    async def create_skill(self, request_model: SkillPackageCreateRequestModel):
        return serialize_response_value(
            await MCPAdminService.create_skill(request_model.model_dump(exclude_none=True))
        )

    async def update_skill(self, skill_id: int, request_model: SkillPackageUpdateRequestModel):
        return serialize_response_value(
            await MCPAdminService.update_skill(
                skill_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def deactivate_skill(self, skill_id: int):
        return serialize_response_value(await MCPAdminService.deactivate_skill(skill_id))

    async def validate_skill_path(self, request_model: SkillPathValidationRequestModel):
        return AdminQueryService.validate_skill_source_path(request_model.source_path)

