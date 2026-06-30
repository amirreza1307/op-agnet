from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentApiKeyCreateRequestModel(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=100)
    expires_at: datetime

    model_config = ConfigDict(str_strip_whitespace=True)
