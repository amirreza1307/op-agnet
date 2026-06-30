from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgnoSessionSchema(ModelSchemaAbstract):
    SESSION_ID: ClassVar[str] = "session_id"
    USER_ID: ClassVar[str] = "user_id"
    WORKFLOW_ID: ClassVar[str] = "workflow_id"
    TEAM_ID: ClassVar[str] = "team_id"
    AGENT_ID: ClassVar[str] = "agent_id"
    SESSION_TYPE: ClassVar[str] = "session_type"
    SESSION_DATA: ClassVar[str] = "session_data"
    AGENT_DATA: ClassVar[str] = "agent_data"
    SUMMARY: ClassVar[str] = "summary"
    RUNS: ClassVar[str] = "runs"
    METADATA: ClassVar[str] = "metadata"
    WORKFLOW_DATA: ClassVar[str] = "workflow_data"
    TEAM_DATA: ClassVar[str] = "team_data"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
