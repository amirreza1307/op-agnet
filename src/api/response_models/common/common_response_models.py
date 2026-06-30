from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApiResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimestampedResponseModel(ApiResponseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None


class MessageResponseModel(ApiResponseModel):
    message: str


class HealthResponseModel(ApiResponseModel):
    status: str


class ReadinessResponseModel(ApiResponseModel):
    status: str
    checks: dict[str, str]

