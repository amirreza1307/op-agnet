from typing import Optional

from fastapi import APIRouter

from api.controllers.v1.admin.resource_controller import ResourceController
from api.request_models.v1.admin.admin_request_models import (
    McpServerCreateRequestModel,
    McpServerTestRequestModel,
    McpServerUpdateRequestModel,
    SkillPackageCreateRequestModel,
    SkillPackageUpdateRequestModel,
    SkillPathValidationRequestModel,
)
from api.response_models.v1.admin.admin_response_models import (
    McpServerDetailResponseModel,
    McpServerResponseModel,
    McpServerSourceListResponseModel,
    McpServerTestResponseModel,
    SkillDetailResponseModel,
    SkillPackageResponseModel,
    SkillPathValidationResponseModel,
    SkillSourceListResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin"])


@router.post("/mcp-servers", response_model=McpServerResponseModel)
async def create_mcp_server(request_data: McpServerCreateRequestModel):
    return await ResourceController().create_mcp_server(request_data)


@router.get("/mcp-servers", response_model=list[McpServerResponseModel])
async def list_mcp_servers(include_inactive: bool = False, search: str | None = None):
    return await ResourceController().list_mcp_servers(include_inactive=include_inactive, search=search)


@router.get("/mcp-servers/sources", response_model=McpServerSourceListResponseModel)
async def list_local_mcp_sources():
    return await ResourceController().list_local_mcp_sources()


@router.get("/mcp-servers/{server_id}", response_model=McpServerDetailResponseModel)
async def get_mcp_server_detail(server_id: int):
    return await ResourceController().mcp_server_detail(server_id)


@router.post("/mcp-servers/{server_id}/test", response_model=McpServerTestResponseModel)
async def test_mcp_server(server_id: int, request_data: Optional[McpServerTestRequestModel] = None):
    return await ResourceController().test_mcp_server(server_id, request_data)


@router.patch("/mcp-servers/{server_id}", response_model=McpServerResponseModel)
async def update_mcp_server(server_id: int, request_data: McpServerUpdateRequestModel):
    return await ResourceController().update_mcp_server(server_id, request_data)


@router.delete("/mcp-servers/{server_id}", response_model=McpServerResponseModel)
async def deactivate_mcp_server(server_id: int):
    return await ResourceController().deactivate_mcp_server(server_id)


@router.get("/skills", response_model=list[SkillPackageResponseModel])
async def list_skills(include_inactive: bool = False, search: str | None = None):
    return await ResourceController().list_skills(include_inactive=include_inactive, search=search)


@router.get("/skills/sources", response_model=SkillSourceListResponseModel)
async def list_skill_sources():
    return await ResourceController().list_skill_sources()


@router.get("/skills/{skill_id}", response_model=SkillDetailResponseModel)
async def get_skill_detail(skill_id: int):
    return await ResourceController().skill_detail(skill_id)


@router.post("/skills", response_model=SkillPackageResponseModel)
async def create_skill(request_data: SkillPackageCreateRequestModel):
    return await ResourceController().create_skill(request_data)


@router.patch("/skills/{skill_id}", response_model=SkillPackageResponseModel)
async def update_skill(skill_id: int, request_data: SkillPackageUpdateRequestModel):
    return await ResourceController().update_skill(skill_id, request_data)


@router.delete("/skills/{skill_id}", response_model=SkillPackageResponseModel)
async def deactivate_skill(skill_id: int):
    return await ResourceController().deactivate_skill(skill_id)


@router.post("/skills/validate-path", response_model=SkillPathValidationResponseModel)
async def validate_skill_source_path(request_data: SkillPathValidationRequestModel):
    return await ResourceController().validate_skill_path(request_data)

