from datetime import datetime
from typing import Any, Optional

from basalam.backbone_orm import ModelAbstract


class LlmRequestLog(ModelAbstract):
    x_ref: Optional[str] = None
    id: int
    scope: str = ""
    model: Optional[str] = None
    messages: Optional[Any] = None
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    def repository(self):
        from database.repositories.main.llm_request_log_repo import LlmRequestLogRepo
        return LlmRequestLogRepo
