import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Schema for requesting an outbound message to be sent to a customer."""
    recipient: str = Field(..., examples=["+14155552671"], description="Recipient phone number.")
    content: str = Field(..., min_length=1, max_length=1600, examples=["Your order #1042 has shipped!"])
    channel: str = Field(default="sms", examples=["sms", "whatsapp"])
    conversation_id: Optional[uuid.UUID] = Field(
        None, description="Optional conversation UUID. If omitted, will be found or created automatically."
    )


class MessageResponse(BaseModel):
    """Schema for message details returned in responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    direction: str = Field(..., examples=["inbound", "outbound"])
    sender: str
    recipient: str
    content: str
    status: str = Field(..., examples=["received", "queued", "sent", "delivered", "failed"])
    provider_message_id: Optional[str] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Schema for conversation metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    channel: str
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Conversation metadata including chronological messages."""
    messages: List[MessageResponse] = []
