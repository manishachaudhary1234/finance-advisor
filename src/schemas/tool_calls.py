from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolCallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class ToolCallRequest(BaseModel):
    request_id: str = Field(..., min_length=6, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    tool_name: str = Field(..., min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    request_id: str
    tool_name: str
    status: ToolCallStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
