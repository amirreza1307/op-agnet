from __future__ import annotations

from typing import Any, Optional

from api.response_models.common.common_response_models import ApiResponseModel


class PlatformRunResponseModel(ApiResponseModel):
    id: Optional[str] = None
    node_id: int
    slug: str
    session_id: Optional[str] = None
    content: Any = None
    status: Optional[str] = None
