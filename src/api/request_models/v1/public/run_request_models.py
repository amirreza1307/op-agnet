from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, model_validator

from api.request_models.common.request_model_abstract import RequestModelAbstract


class PlatformRunRequestModel(RequestModelAbstract):
    node_id: Optional[int] = None
    slug: Optional[str] = None
    message: str = Field(min_length=1)
    session_id: Optional[str] = None
    principal_id: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    instructions: Optional[list[str]] = None
    stream_events: Optional[bool] = None
    output_schema: Optional[dict[str, Any]] = None
    structured_outputs: Optional[bool] = None

    @model_validator(mode="after")
    def validate_node_reference(self) -> "PlatformRunRequestModel":
        if bool(self.node_id is None) == bool(self.slug is None):
            raise ValueError("Exactly one of node_id or slug must be provided")
        return self

