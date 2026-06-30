from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class McpServerSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    SLUG: ClassVar[str] = "slug"
    NAME: ClassVar[str] = "name"
    TRANSPORT: ClassVar[str] = "transport"
    COMMAND: ClassVar[str] = "command"
    URL: ClassVar[str] = "url"
    WORKING_DIRECTORY: ClassVar[str] = "working_directory"
    ENV_JSON: ClassVar[str] = "env_json"
    HEADERS_JSON: ClassVar[str] = "headers_json"
    INCLUDE_TOOLS_JSON: ClassVar[str] = "include_tools_json"
    EXCLUDE_TOOLS_JSON: ClassVar[str] = "exclude_tools_json"
    TOOL_NAME_PREFIX: ClassVar[str] = "tool_name_prefix"
    TIMEOUT_SECONDS: ClassVar[str] = "timeout_seconds"
    REFRESH_CONNECTION: ClassVar[str] = "refresh_connection"
    ALLOW_PARTIAL_FAILURE: ClassVar[str] = "allow_partial_failure"
    IS_ACTIVE: ClassVar[str] = "is_active"
    IS_PUBLIC: ClassVar[str] = "is_public"
    PUBLIC_NAME: ClassVar[str] = "public_name"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    CREATED_BY: ClassVar[str] = "created_by"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
