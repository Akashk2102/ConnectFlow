import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkflowActionResponse(BaseModel):
    """Schema for workflow tool action records."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    action_type: str
    status: str = Field(..., examples=["pending_approval", "executed", "rejected", "failed"])
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    requires_human_approval: bool
    approved_by: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class ApproveActionRequest(BaseModel):
    approved_by: Optional[str] = Field(default="admin@business.com", description="Email or user ID of approving manager.")


class RejectActionRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Justification for rejecting the AI proposed action.")
    rejected_by: Optional[str] = Field(default="admin@business.com")
