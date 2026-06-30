from fastapi import APIRouter

from api.controllers.v1.admin.tool_controller import ToolController
from api.request_models.v1.admin.admin_request_models import (
    ActionCreateRequestModel,
    ActionUpdateRequestModel,
    ToolActionBindingRequestModel,
    ToolCreateRequestModel,
    ToolKnowledgeNodeCreateRequestModel,
    ToolKnowledgeNodeUpdateRequestModel,
    ToolUpdateRequestModel,
)
from api.response_models.v1.admin.admin_response_models import (
    ActionDetailResponseModel,
    ToolActionBindingResponseModel,
    ToolActionResponseModel,
    ToolDetailResponseModel,
    ToolKnowledgeNodeResponseModel,
    ToolResponseModel,
    ToolScriptListResponseModel,
    ToolSummaryResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin"])


@router.post("/tools", response_model=ToolResponseModel)
async def create_tool(request_data: ToolCreateRequestModel):
    return await ToolController().create(request_data)


@router.get("/tools", response_model=list[ToolSummaryResponseModel])
async def list_tools(include_inactive: bool = False, search: str | None = None):
    return await ToolController().list(include_inactive=include_inactive, search=search)


@router.get("/tools/scripts", response_model=ToolScriptListResponseModel)
async def list_tool_scripts():
    return await ToolController().list_scripts()


@router.get("/tools/{tool_id}/detail", response_model=ToolDetailResponseModel)
async def get_tool_detail(tool_id: int):
    return await ToolController().detail(tool_id)


@router.patch("/tools/{tool_id}", response_model=ToolResponseModel)
async def update_tool(tool_id: int, request_data: ToolUpdateRequestModel):
    return await ToolController().update(tool_id, request_data)


@router.delete("/tools/{tool_id}", response_model=ToolResponseModel)
async def deactivate_tool(tool_id: int):
    return await ToolController().deactivate(tool_id)


@router.post("/actions", response_model=ToolActionResponseModel)
async def create_action(request_data: ActionCreateRequestModel):
    return await ToolController().create_action(request_data)


@router.get("/actions", response_model=list[ToolActionResponseModel])
async def list_actions(include_inactive: bool = False, search: str | None = None):
    return await ToolController().list_actions(include_inactive=include_inactive, search=search)


@router.get("/actions/{action_id}", response_model=ActionDetailResponseModel)
async def get_action_detail(action_id: int):
    return await ToolController().action_detail(action_id)


@router.patch("/actions/{action_id}", response_model=ToolActionResponseModel)
async def update_action(action_id: int, request_data: ActionUpdateRequestModel):
    return await ToolController().update_action(action_id, request_data)


@router.delete("/actions/{action_id}", response_model=ToolActionResponseModel)
async def deactivate_action(action_id: int):
    return await ToolController().deactivate_action(action_id)


@router.post("/tools/{tool_id}/actions/bind", response_model=ToolActionBindingResponseModel)
async def bind_action(tool_id: int, request_data: ToolActionBindingRequestModel):
    return await ToolController().bind_action(tool_id, request_data)


@router.delete("/tools/{tool_id}/actions/bind/{binding_id}", response_model=ToolActionBindingResponseModel)
async def unbind_action(tool_id: int, binding_id: int):
    return await ToolController().unbind_action(tool_id, binding_id)


@router.post(
    "/tool-knowledge-nodes",
    response_model=ToolKnowledgeNodeResponseModel,
)
async def create_tool_knowledge_node(
    request_data: ToolKnowledgeNodeCreateRequestModel,
):
    return await ToolController().create_knowledge_node(request_data)


@router.get(
    "/tool-knowledge-nodes",
    response_model=list[ToolKnowledgeNodeResponseModel],
)
async def list_tool_knowledge_nodes(
    tool_slug: str | None = None,
    include_inactive: bool = False,
    search: str | None = None,
):
    return await ToolController().list_knowledge_nodes(
        tool_slug=tool_slug,
        include_inactive=include_inactive,
        search=search,
    )


@router.get(
    "/tool-knowledge-nodes/{knowledge_node_id}",
    response_model=ToolKnowledgeNodeResponseModel,
)
async def get_tool_knowledge_node(knowledge_node_id: int):
    return await ToolController().get_knowledge_node(knowledge_node_id)


@router.patch(
    "/tool-knowledge-nodes/{knowledge_node_id}",
    response_model=ToolKnowledgeNodeResponseModel,
)
async def update_tool_knowledge_node(
    knowledge_node_id: int,
    request_data: ToolKnowledgeNodeUpdateRequestModel,
):
    return await ToolController().update_knowledge_node(
        knowledge_node_id, request_data
    )


@router.delete(
    "/tool-knowledge-nodes/{knowledge_node_id}",
    response_model=ToolKnowledgeNodeResponseModel,
)
async def deactivate_tool_knowledge_node(knowledge_node_id: int):
    return await ToolController().deactivate_knowledge_node(knowledge_node_id)

