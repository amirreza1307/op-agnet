from typing import Any, Optional

from typing import Literal

from pydantic import BaseModel, Field

from api.request_models.common.request_model_abstract import RequestModelAbstract
from api.request_models.v1.public.run_request_models import PlatformRunRequestModel


# â”€â”€â”€ Nodes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class NodeCreateRequestModel(BaseModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
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


class NodeUpdateRequestModel(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None
    session_table: Optional[str] = None
    runtime_config_json: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    public_name: Optional[str] = None
    image_file_id: Optional[int] = None
    priority: Optional[int] = None
    version: Optional[int] = None
    metadata_json: Optional[dict[str, Any]] = None


class EdgeCreateRequestModel(BaseModel):
    parent_node_id: int
    child_node_id: int
    priority: int = 0
    is_active: bool = True
    member_instructions_json: list[str] = Field(default_factory=list)
    metadata_json: Optional[dict[str, Any]] = None


class NodeToolBindingRequestModel(BaseModel):
    tool_id: int
    priority: int = 0
    is_enabled: bool = True
    binding_mode: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class NodeMcpBindingRequestModel(BaseModel):
    mcp_server_id: int
    priority: int = 0
    is_enabled: bool = True
    binding_mode: Optional[str] = None
    header_template_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class NodeSkillBindingRequestModel(BaseModel):
    skill_package_id: int
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class AgentChannelCreateRequestModel(BaseModel):
    channel_type: Literal["telegram", "bale"]
    bot_token: str = Field(min_length=1)
    name: Optional[str] = None
    api_base_url: Optional[str] = None
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None
    verify_bot: bool = True


class AgentChannelUpdateRequestModel(BaseModel):
    bot_token: Optional[str] = None
    name: Optional[str] = None
    api_base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    metadata_json: Optional[dict[str, Any]] = None
    verify_bot: bool = True


class AgentChannelSetWebhookRequestModel(BaseModel):
    public_base_url: Optional[str] = None
    drop_pending_updates: bool = False
    allowed_updates: Optional[list[str]] = None


# â”€â”€â”€ Resources (MCP servers, skills) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class McpServerCreateRequestModel(BaseModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    transport: str = Field(min_length=1)
    local_source_path: Optional[str] = None
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


class McpServerUpdateRequestModel(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    transport: Optional[str] = None
    local_source_path: Optional[str] = None
    command: Optional[str] = None
    url: Optional[str] = None
    working_directory: Optional[str] = None
    env_json: Optional[dict[str, str]] = None
    headers_json: Optional[dict[str, Any]] = None
    include_tools_json: Optional[list[str]] = None
    exclude_tools_json: Optional[list[str]] = None
    tool_name_prefix: Optional[str] = None
    timeout_seconds: Optional[int] = None
    refresh_connection: Optional[bool] = None
    allow_partial_failure: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    public_name: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class McpServerTestRequestModel(BaseModel):
    header_template_json: Optional[dict[str, Any]] = None
    session_state: dict[str, Any] = Field(default_factory=dict)


class SkillPackageCreateRequestModel(BaseModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    source_path: str = Field(min_length=1)
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None


class SkillPackageUpdateRequestModel(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    source_path: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    public_name: Optional[str] = None


class SkillPathValidationRequestModel(BaseModel):
    source_path: str = Field(min_length=1)


# â”€â”€â”€ Tools / actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ToolActionInputModel(BaseModel):
    action_id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None
    description: str = ""
    constructor_params: dict[str, Any] = Field(default_factory=dict)
    response_title: Optional[str] = None
    priority: int = 0
    is_active: bool = True


class ToolCreateRequestModel(BaseModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tool_type: str = Field(min_length=1)
    script_slug: Optional[str] = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    required_tool_ids: list[int] = Field(default_factory=list)
    show_result: bool = False
    action_only_name: Optional[str] = None
    action_only_description: Optional[str] = None
    rule_method: Optional[str] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    api_url: Optional[str] = None
    api_method: str = "GET"
    api_headers: Optional[dict[str, Any]] = None
    api_body_template: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    actions: list[ToolActionInputModel] = Field(default_factory=list)


class ToolUpdateRequestModel(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tool_type: Optional[str] = None
    script_slug: Optional[str] = None
    parameters: Optional[list[dict[str, Any]]] = None
    required_tool_ids: Optional[list[int]] = None
    show_result: Optional[bool] = None
    action_only_name: Optional[str] = None
    action_only_description: Optional[str] = None
    rule_method: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    public_name: Optional[str] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[dict[str, Any]] = None
    api_body_template: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    actions: Optional[list[ToolActionInputModel]] = None


class ActionCreateRequestModel(BaseModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    is_active: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class ActionUpdateRequestModel(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[dict[str, Any]] = None


class ToolActionBindingRequestModel(BaseModel):
    action_id: int
    constructor_params: dict[str, Any] = Field(default_factory=dict)
    response_title: Optional[str] = None
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class ToolKnowledgeNodeCreateRequestModel(BaseModel):
    tool_slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    priority: int = 0
    is_active: bool = True


class ToolKnowledgeNodeUpdateRequestModel(BaseModel):
    tool_slug: Optional[str] = Field(default=None, min_length=1)
    title: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = Field(default=None, min_length=1)
    priority: Optional[int] = None
    is_active: Optional[bool] = None


# â”€â”€â”€ Run / vendor activation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PlatformAdminRunRequestModel(PlatformRunRequestModel):
    pass

