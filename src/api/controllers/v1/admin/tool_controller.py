from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.admin_request_models import (
    ActionCreateRequestModel,
    ActionUpdateRequestModel,
    ToolActionBindingRequestModel,
    ToolCreateRequestModel,
    ToolKnowledgeNodeCreateRequestModel,
    ToolKnowledgeNodeUpdateRequestModel,
    ToolUpdateRequestModel,
)
from api.serializers import serialize_response_value
from services.platform.admin.queries.admin_query_service import AdminQueryService
from services.platform.admin.tools.tool_admin_service import ToolAdminService
from services.platform.admin.tools.tool_knowledge_node_admin import (
    ToolKnowledgeNodeAdmin,
)


class ToolController(ControllerAbstract):

    # â”€â”€â”€ Tools â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def create(self, request_model: ToolCreateRequestModel):
        return serialize_response_value(
            await ToolAdminService.create_tool(request_model.model_dump())
        )

    async def list(self, include_inactive: bool = False, search: str | None = None):
        return await AdminQueryService.list_tools(
            include_inactive=include_inactive, search=search
        )

    async def list_scripts(self):
        return ToolAdminService.list_tool_scripts()

    async def detail(self, tool_id: int):
        return await AdminQueryService.get_tool_detail(tool_id)

    async def update(self, tool_id: int, request_model: ToolUpdateRequestModel):
        return serialize_response_value(
            await ToolAdminService.update_tool(
                tool_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def deactivate(self, tool_id: int):
        return serialize_response_value(await ToolAdminService.deactivate_tool(tool_id))

    # â”€â”€â”€ Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def create_action(self, request_model: ActionCreateRequestModel):
        return serialize_response_value(
            await ToolAdminService.create_action(
                request_model.model_dump(exclude_none=True)
            )
        )

    async def list_actions(self, include_inactive: bool = False, search: str | None = None):
        return await AdminQueryService.list_actions(
            include_inactive=include_inactive, search=search
        )

    async def action_detail(self, action_id: int):
        return await AdminQueryService.get_action_detail(action_id)

    async def update_action(self, action_id: int, request_model: ActionUpdateRequestModel):
        return serialize_response_value(
            await ToolAdminService.update_action(
                action_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def deactivate_action(self, action_id: int):
        return serialize_response_value(await ToolAdminService.deactivate_action(action_id))

    async def bind_action(self, tool_id: int, request_model: ToolActionBindingRequestModel):
        return serialize_response_value(
            await ToolAdminService.bind_action(
                tool_id, request_model.model_dump(exclude_none=True)
            )
        )

    async def unbind_action(self, tool_id: int, binding_id: int):
        _ = tool_id
        return serialize_response_value(await ToolAdminService.unbind_action(binding_id))

    # Tool knowledge nodes

    async def create_knowledge_node(
        self, request_model: ToolKnowledgeNodeCreateRequestModel
    ):
        return serialize_response_value(
            await ToolKnowledgeNodeAdmin.create(request_model.model_dump())
        )

    async def list_knowledge_nodes(
        self,
        *,
        tool_slug: str | None = None,
        include_inactive: bool = False,
        search: str | None = None,
    ):
        return serialize_response_value(
            await ToolKnowledgeNodeAdmin.list(
                tool_slug=tool_slug,
                include_inactive=include_inactive,
                search=search,
            )
        )

    async def get_knowledge_node(self, knowledge_node_id: int):
        return serialize_response_value(
            await ToolKnowledgeNodeAdmin.get(knowledge_node_id)
        )

    async def update_knowledge_node(
        self,
        knowledge_node_id: int,
        request_model: ToolKnowledgeNodeUpdateRequestModel,
    ):
        return serialize_response_value(
            await ToolKnowledgeNodeAdmin.update(
                knowledge_node_id,
                request_model.model_dump(exclude_none=True),
            )
        )

    async def deactivate_knowledge_node(self, knowledge_node_id: int):
        return serialize_response_value(
            await ToolKnowledgeNodeAdmin.deactivate(knowledge_node_id)
        )

