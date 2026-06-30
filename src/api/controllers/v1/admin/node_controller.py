from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.admin_request_models import (
    EdgeCreateRequestModel,
    NodeCreateRequestModel,
    NodeMcpBindingRequestModel,
    NodeSkillBindingRequestModel,
    NodeToolBindingRequestModel,
    NodeUpdateRequestModel,
)
from api.serializers import serialize_response_value
from services.platform.admin.nodes.edge_admin_service import EdgeAdminService
from services.platform.admin.mcp.mcp_admin_service import MCPAdminService
from services.platform.admin.nodes.node_admin_service import NodeAdminService
from services.platform.admin.queries.admin_query_service import AdminQueryService
from services.platform.admin.tools.tool_admin_service import ToolAdminService
from services.platform.graph.node_registry_service import NodeRegistryService


class NodeController(ControllerAbstract):

    async def list(self, include_inactive: bool = False, search: str | None = None):
        return await AdminQueryService.list_nodes(
            include_inactive=include_inactive, search=search
        )

    async def get(self, node_id: int):
        return serialize_response_value(await NodeRegistryService.resolve(node_id=node_id))

    async def detail(self, node_id: int):
        return await AdminQueryService.get_node_detail(node_id)

    async def get_by_slug(self, slug: str):
        return serialize_response_value(await NodeRegistryService.resolve(slug=slug))

    async def graph(self, node_id: int):
        node = await NodeRegistryService.resolve(node_id=node_id)
        return await NodeRegistryService.get_graph(node)

    async def create(self, request_model: NodeCreateRequestModel):
        return serialize_response_value(
            await NodeAdminService.create_node(request_model.model_dump())
        )

    async def update(self, node_id: int, request_model: NodeUpdateRequestModel):
        return serialize_response_value(
            await NodeAdminService.update_node(
                node_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def deactivate(self, node_id: int):
        return serialize_response_value(await NodeAdminService.deactivate_node(node_id))

    async def create_edge(self, request_model: EdgeCreateRequestModel):
        return serialize_response_value(
            await EdgeAdminService.create_edge(request_model.model_dump())
        )

    async def deactivate_edge(self, edge_id: int):
        return serialize_response_value(await EdgeAdminService.deactivate_edge(edge_id))

    async def bind_tool(self, node_id: int, request_model: NodeToolBindingRequestModel):
        return serialize_response_value(
            await ToolAdminService.bind_tool(
                node_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def unbind_tool(self, node_id: int, binding_id: int):
        _ = node_id
        return serialize_response_value(await ToolAdminService.unbind_tool(binding_id))

    async def bind_mcp(self, node_id: int, request_model: NodeMcpBindingRequestModel):
        return serialize_response_value(
            await MCPAdminService.bind_mcp(
                node_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def unbind_mcp(self, node_id: int, binding_id: int):
        _ = node_id
        return serialize_response_value(await MCPAdminService.unbind_mcp(binding_id))

    async def bind_skill(self, node_id: int, request_model: NodeSkillBindingRequestModel):
        return serialize_response_value(
            await MCPAdminService.bind_skill(
                node_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def unbind_skill(self, node_id: int, binding_id: int):
        _ = node_id
        return serialize_response_value(await MCPAdminService.unbind_skill(binding_id))

