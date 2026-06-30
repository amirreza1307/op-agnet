"""Output schemas for the Numberland order SDK."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NumberlandOrder(BaseModel):
    """One order row returned by the Numberland admin orders endpoint."""

    model_config = ConfigDict(extra="allow")

    id: Optional[int] = Field(default=None)
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    user_id: Optional[int] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)


class NumberlandOrdersListResponse(BaseModel):
    """``GET /v1/admin/orders`` response.

    The service may return either a plain list or an envelope with ``data`` /
    pagination metadata. Unknown fields are preserved.
    """

    model_config = ConfigDict(extra="allow")

    data: List[NumberlandOrder] = Field(default_factory=list)
    total: Optional[int] = Field(default=None)
    limit: Optional[int] = Field(default=None)
    offset: Optional[int] = Field(default=None)
    raw: Optional[Any] = Field(default=None, exclude=True)

