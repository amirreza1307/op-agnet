from fastapi import APIRouter

from api.controllers.v1.admin.node_controller import NodeController
from api.request_models.v1.admin.admin_request_models import (
    EdgeCreateRequestModel,
    NodeCreateRequestModel,
    NodeMcpBindingRequestModel,
    NodeSkillBindingRequestModel,
    NodeToolBindingRequestModel,
    NodeUpdateRequestModel,
)
from api.response_models.v1.admin.admin_response_models import (
    AgentNodeEdgeResponseModel,
    AgentNodeGraphResponseModel,
    AgentNodeResponseModel,
    AgentNodeSummaryResponseModel,
    NodeDetailResponseModel,
    NodeMcpBindingResponseModel,
    NodeSkillBindingResponseModel,
    NodeToolBindingResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin"])


@router.get("/nodes", response_model=list[AgentNodeSummaryResponseModel])
async def list_nodes(include_inactive: bool = False, search: str | None = None):
    return await NodeController().list(include_inactive=include_inactive, search=search)


@router.get("/nodes/{node_id}", response_model=AgentNodeResponseModel)
async def get_node(node_id: int):
    return await NodeController().get(node_id)


@router.get("/nodes/{node_id}/detail", response_model=NodeDetailResponseModel)
async def get_node_detail(node_id: int):
    return await NodeController().detail(node_id)


@router.get("/nodes/by-slug/{slug}", response_model=AgentNodeResponseModel)
async def get_node_by_slug(slug: str):
    return await NodeController().get_by_slug(slug)


@router.get("/nodes/{node_id}/graph", response_model=AgentNodeGraphResponseModel)
async def get_node_graph(node_id: int):
    return await NodeController().graph(node_id)


@router.post("/nodes", response_model=AgentNodeResponseModel)
async def create_node(request_data: NodeCreateRequestModel):
    return await NodeController().create(request_data)


@router.patch("/nodes/{node_id}", response_model=AgentNodeResponseModel)
async def update_node(node_id: int, request_data: NodeUpdateRequestModel):
    return await NodeController().update(node_id, request_data)


@router.delete("/nodes/{node_id}", response_model=AgentNodeResponseModel)
async def deactivate_node(node_id: int):
    return await NodeController().deactivate(node_id)


@router.post("/edges", response_model=AgentNodeEdgeResponseModel)
async def create_edge(request_data: EdgeCreateRequestModel):
    return await NodeController().create_edge(request_data)


@router.delete("/edges/{edge_id}", response_model=AgentNodeEdgeResponseModel)
async def deactivate_edge(edge_id: int):
    return await NodeController().deactivate_edge(edge_id)


@router.post("/nodes/{node_id}/tools/bind", response_model=NodeToolBindingResponseModel)
async def bind_tool(node_id: int, request_data: NodeToolBindingRequestModel):
    return await NodeController().bind_tool(node_id, request_data)


@router.delete("/nodes/{node_id}/tools/bind/{binding_id}", response_model=NodeToolBindingResponseModel)
async def unbind_tool(node_id: int, binding_id: int):
    return await NodeController().unbind_tool(node_id, binding_id)


@router.post("/nodes/{node_id}/mcp/bind", response_model=NodeMcpBindingResponseModel)
async def bind_mcp(node_id: int, request_data: NodeMcpBindingRequestModel):
    return await NodeController().bind_mcp(node_id, request_data)


@router.delete("/nodes/{node_id}/mcp/bind/{binding_id}", response_model=NodeMcpBindingResponseModel)
async def unbind_mcp(node_id: int, binding_id: int):
    return await NodeController().unbind_mcp(node_id, binding_id)


@router.post("/nodes/{node_id}/skills/bind", response_model=NodeSkillBindingResponseModel)
async def bind_skill(node_id: int, request_data: NodeSkillBindingRequestModel):
    return await NodeController().bind_skill(node_id, request_data)


@router.delete("/nodes/{node_id}/skills/bind/{binding_id}", response_model=NodeSkillBindingResponseModel)
async def unbind_skill(node_id: int, binding_id: int):
    return await NodeController().unbind_skill(node_id, binding_id)

