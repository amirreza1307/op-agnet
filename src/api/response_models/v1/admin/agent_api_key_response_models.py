from datetime import datetime
from typing import Optional

from api.response_models.common.common_response_models import ApiResponseModel


class AgentApiKeyResponseModel(ApiResponseModel):
    id: int
    node_id: int
    name: str
    key_prefix: str
    expires_at: datetime
    is_active: bool
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentApiKeyCreatedResponseModel(AgentApiKeyResponseModel):
    api_key: str
