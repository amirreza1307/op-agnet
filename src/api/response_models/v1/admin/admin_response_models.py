from __future__ import annotations

from typing import Any, Optional

from pydantic import ConfigDict, Field

from api.response_models.common.common_response_models import ApiResponseModel, TimestampedResponseModel


# â”€â”€â”€ Platform config / discovery / analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PlatformDefaultRuntimeConfigResponseModel(ApiResponseModel):
    default_model_id: Optional[str] = None
    default_model_provider: Optional[str] = None
    default_base_url: Optional[str] = None
    default_session_table: Optional[str] = None


class McpServerSourceItemResponseModel(ApiResponseModel):
    source_path: str
    slug: str
    display_name: str
    entrypoint: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class McpServerSourceListResponseModel(ApiResponseModel):
    items: list[McpServerSourceItemResponseModel] = Field(default_factory=list)
    mcp_root_dir: str = ""


class SkillSourceItemResponseModel(ApiResponseModel):
    source_path: str
    display_name: str
    has_skill_file: bool = True

    model_config = ConfigDict(extra="allow")


class SkillSourceListResponseModel(ApiResponseModel):
    items: list[SkillSourceItemResponseModel] = Field(default_factory=list)


class RegisteredToolResponseModel(ApiResponseModel):
    slug: str
    name_fa: str
    class_name: str
    module: str


class ToolScriptListResponseModel(ApiResponseModel):
    tools: list[RegisteredToolResponseModel] = Field(default_factory=list)


class PlatformOverviewCountsResponseModel(ApiResponseModel):
    nodes: int
    edges: int
    tools: int
    mcp_servers: int
    skills: int
    tool_actions: int


class PlatformOverviewCacheResponseModel(ApiResponseModel):
    loaded: bool
    global_base_prompt_enabled: bool = False


class PlatformOverviewRuntimeResponseModel(ApiResponseModel):
    traces_enabled: bool


class PlatformOverviewResponseModel(ApiResponseModel):
    counts: PlatformOverviewCountsResponseModel
    cache: PlatformOverviewCacheResponseModel
    runtime: PlatformOverviewRuntimeResponseModel


class PlatformCacheRefreshResponseModel(ApiResponseModel):
    message: str
    overview: PlatformOverviewResponseModel


class AgentNodeResponseModel(TimestampedResponseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    system_prompt: str = ""
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None
    session_table: Optional[str] = None
    runtime_config_json: Optional[dict[str, Any]] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    image_file_id: Optional[int] = None
    priority: int = 0
    version: int = 1
    metadata_json: Optional[dict[str, Any]] = None
    created_by: Optional[int] = None


class AgentNodeSummaryResponseModel(AgentNodeResponseModel):
    child_count: int = 0
    parent_agent_names: list[str] = Field(default_factory=list)
    tool_binding_count: int = 0
    mcp_binding_count: int = 0
    skill_binding_count: int = 0
    channel_count: int = 0


class AgentNodeGraphResponseModel(ApiResponseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    system_prompt: str = ""
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_base_url: Optional[str] = None
    session_table: Optional[str] = None
    runtime_config_json: Optional[dict[str, Any]] = None
    children: list["AgentNodeGraphResponseModel"] = Field(default_factory=list)


class AgentNodeEdgeResponseModel(TimestampedResponseModel):
    id: int
    parent_node_id: int
    child_node_id: int
    priority: int = 0
    is_active: bool = True
    member_instructions_json: list[str] = Field(default_factory=list)
    metadata_json: Optional[dict[str, Any]] = None


class ToolResponseModel(TimestampedResponseModel):
    id: int
    slug: Optional[str] = None
    name: str
    description: str
    progress_label: Optional[str] = None
    progress_visual_type: Optional[str] = None
    progress_visual_value: Optional[str] = None
    tool_type: str
    user_types: list[str] = Field(default_factory=list)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    required_tool_ids: list[int] = Field(default_factory=list)
    show_result: bool = False
    action_only_name: Optional[str] = None
    action_only_description: Optional[str] = None
    rule_method: Optional[str] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    agent_id: Optional[int] = None
    api_url: Optional[str] = None
    api_method: str = "GET"
    api_headers: Optional[dict[str, Any]] = None
    api_body_template: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_by: Optional[int] = None


class ToolSummaryResponseModel(ToolResponseModel):
    action_count: int = 0


class ToolActionResponseModel(TimestampedResponseModel):
    id: int
    tool_id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None
    description: str = ""
    fa_name: Optional[str] = None
    fa_description: Optional[str] = None
    constructor_params: dict[str, Any] = Field(default_factory=dict)
    response_title: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class ToolActionBindingResponseModel(TimestampedResponseModel):
    id: int
    tool_id: int
    action_id: int
    constructor_params: dict[str, Any] = Field(default_factory=dict)
    response_title: Optional[str] = None
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class ToolKnowledgeNodeResponseModel(TimestampedResponseModel):
    id: int
    tool_slug: str
    title: str
    content: str
    priority: int = 0
    is_active: bool = True


class NodeToolBindingResponseModel(TimestampedResponseModel):
    id: int
    node_id: int
    tool_id: int
    priority: int = 0
    is_enabled: bool = True
    binding_mode: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class McpServerResponseModel(TimestampedResponseModel):
    id: int
    slug: str
    name: str
    transport: str
    local_source_path: Optional[str] = None
    local_entrypoint: Optional[str] = None
    command: Optional[str] = None
    url: Optional[str] = None
    working_directory: Optional[str] = None
    env_json: Optional[dict[str, str]] = None
    headers_json: Optional[dict[str, Any]] = None
    include_tools_json: Optional[list[str]] = None
    exclude_tools_json: Optional[list[str]] = None
    tool_name_prefix: Optional[str] = None
    timeout_seconds: int = 15
    refresh_connection: bool = False
    allow_partial_failure: bool = False
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_by: Optional[int] = None


class NodeMcpBindingResponseModel(TimestampedResponseModel):
    id: int
    node_id: int
    mcp_server_id: int
    priority: int = 0
    is_enabled: bool = True
    binding_mode: Optional[str] = None
    header_template_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class SkillPackageResponseModel(TimestampedResponseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    source_path: str
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    created_by: Optional[int] = None


class NodeSkillBindingResponseModel(TimestampedResponseModel):
    id: int
    node_id: int
    skill_package_id: int
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class AgentChannelResponseModel(TimestampedResponseModel):
    id: int
    node_id: int
    channel_type: str
    name: str
    token_hint: str
    api_base_url: str
    webhook_url: Optional[str] = None
    suggested_webhook_url: Optional[str] = None
    bot_id: Optional[str] = None
    bot_username: Optional[str] = None
    bot_display_name: Optional[str] = None
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None
    last_verified_at: Optional[Any] = None
    last_webhook_at: Optional[Any] = None


class AgentChannelOperationResponseModel(ApiResponseModel):
    ok: bool
    channel: AgentChannelResponseModel
    bot: Optional[dict[str, Any]] = None
    webhook: Optional[dict[str, Any]] = None
    webhook_url: Optional[str] = None


class AgentNodeEdgeWithChildResponseModel(AgentNodeEdgeResponseModel):
    child: Optional[AgentNodeResponseModel] = None


class AgentNodeEdgeWithParentResponseModel(AgentNodeEdgeResponseModel):
    parent: Optional[AgentNodeResponseModel] = None


class NodeToolBindingWithToolResponseModel(NodeToolBindingResponseModel):
    tool: Optional[ToolResponseModel] = None


class NodeToolBindingWithNodeResponseModel(NodeToolBindingResponseModel):
    node: Optional[AgentNodeResponseModel] = None


class ToolActionBindingWithActionResponseModel(ToolActionBindingResponseModel):
    action: Optional[ToolActionResponseModel] = None


class ToolActionBindingWithToolResponseModel(ToolActionBindingResponseModel):
    tool: Optional[ToolResponseModel] = None


class NodeMcpBindingWithServerResponseModel(NodeMcpBindingResponseModel):
    mcp_server: Optional[McpServerResponseModel] = None


class NodeMcpBindingWithNodeResponseModel(NodeMcpBindingResponseModel):
    node: Optional[AgentNodeResponseModel] = None


class NodeSkillBindingWithPackageResponseModel(NodeSkillBindingResponseModel):
    skill_package: Optional[SkillPackageResponseModel] = None


class NodeSkillBindingWithNodeResponseModel(NodeSkillBindingResponseModel):
    node: Optional[AgentNodeResponseModel] = None


class NodeDetailResponseModel(ApiResponseModel):
    node: AgentNodeResponseModel
    graph: AgentNodeGraphResponseModel
    children: list[AgentNodeEdgeWithChildResponseModel] = Field(default_factory=list)
    parents: list[AgentNodeEdgeWithParentResponseModel] = Field(default_factory=list)
    tool_bindings: list[NodeToolBindingWithToolResponseModel] = Field(default_factory=list)
    mcp_bindings: list[NodeMcpBindingWithServerResponseModel] = Field(default_factory=list)
    skill_bindings: list[NodeSkillBindingWithPackageResponseModel] = Field(default_factory=list)
    channels: list[AgentChannelResponseModel] = Field(default_factory=list)


class ToolDetailResponseModel(ApiResponseModel):
    tool: ToolResponseModel
    action_bindings: list[ToolActionBindingWithActionResponseModel] = Field(default_factory=list)
    node_bindings: list[NodeToolBindingWithNodeResponseModel] = Field(default_factory=list)


class ActionDetailResponseModel(ApiResponseModel):
    action: ToolActionResponseModel
    tool_bindings: list[ToolActionBindingWithToolResponseModel] = Field(default_factory=list)


class McpServerDetailResponseModel(ApiResponseModel):
    mcp_server: McpServerResponseModel
    node_bindings: list[NodeMcpBindingWithNodeResponseModel] = Field(default_factory=list)


class SkillDetailResponseModel(ApiResponseModel):
    skill_package: SkillPackageResponseModel
    resolved_source_path: str
    node_bindings: list[NodeSkillBindingWithNodeResponseModel] = Field(default_factory=list)


class PlatformCatalogResponseModel(ApiResponseModel):
    nodes: list[AgentNodeSummaryResponseModel] = Field(default_factory=list)
    tools: list[ToolSummaryResponseModel] = Field(default_factory=list)
    actions: list[ToolActionResponseModel] = Field(default_factory=list)
    mcp_servers: list[McpServerResponseModel] = Field(default_factory=list)
    skills: list[SkillPackageResponseModel] = Field(default_factory=list)


class AgnoSessionSummaryResponseModel(ApiResponseModel):
    session_id: str
    user_id: Optional[str] = None
    workflow_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_type: str = ""
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    run_count: int = 0
    has_summary: bool = False


class AgnoSessionDetailResponseModel(AgnoSessionSummaryResponseModel):
    session_data: Optional[dict[str, Any]] = None
    agent_data: Optional[dict[str, Any]] = None
    summary: Optional[dict[str, Any]] = None
    runs: list[Any] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None
    workflow_data: Optional[dict[str, Any]] = None
    team_data: Optional[dict[str, Any]] = None
    x_ref: Optional[str] = None


class AgnoSessionListResponseModel(ApiResponseModel):
    items: list[AgnoSessionSummaryResponseModel] = Field(default_factory=list)
    total: int
    page: int
    limit: int


class McpServerTestResponseModel(ApiResponseModel):
    ok: bool
    transport: str
    tool_count: int = 0
    sample_tools: list[dict[str, Any]] = Field(default_factory=list)
    sample_result_json: Optional[dict[str, Any]] = None
    resolved_working_directory: Optional[str] = None
    tool_wrapper_type: Optional[str] = None
    message: str


class SkillPathValidationResponseModel(ApiResponseModel):
    ok: bool
    source_path: str
    resolved_path: str
    exists: bool
    is_directory: bool


AgentNodeGraphResponseModel.model_rebuild()

