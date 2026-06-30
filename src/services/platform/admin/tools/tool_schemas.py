"""Pydantic schemas for tool admin payloads."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ToolUpdateSchema(BaseModel):
    """Strict allow-list for ``ToolAdmin.update_tool`` input.

    Replaces the historical 20-key dict comprehension. ``extra="forbid"``
    rejects unknown keys (e.g. typos like ``api_methode``) at the API
    boundary; every field is optional so callers may patch any subset.
    """

    model_config = ConfigDict(extra="forbid")

    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    progress_label: Optional[str] = None
    progress_visual_type: Optional[str] = None
    progress_visual_value: Optional[str] = None
    tool_type: Optional[str] = None
    parameters: Optional[Any] = None
    required_tool_ids: Optional[Any] = None
    show_result: Optional[bool] = None
    action_only_name: Optional[str] = None
    action_only_description: Optional[str] = None
    rule_method: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    public_name: Optional[str] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[Any] = None
    api_body_template: Optional[str] = None
    metadata_json: Optional[Any] = None
    created_by: Optional[Any] = None
