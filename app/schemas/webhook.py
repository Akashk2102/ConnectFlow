from typing import Optional
from pydantic import BaseModel, Field


class InboundMessageWebhook(BaseModel):
    """
    Schema representing incoming SMS/WhatsApp webhook payloads.
    Matches standard provider fields (e.g., Plivo / Twilio).
    """
    From: str = Field(..., description="Customer sender phone number in E.164 format.")
    To: str = Field(..., description="Business destination phone number.")
    Text: str = Field(..., description="Message text body.")
    MessageUUID: str = Field(..., description="Unique message UUID provided by the telecom gateway.")
    Type: str = Field(default="sms", description="Message type: sms, mms, or whatsapp.")
    Units: Optional[int] = Field(default=1, description="Number of message segments.")


class DeliveryReportWebhook(BaseModel):
    """
    Schema for delivery receipts and status update callbacks.
    """
    MessageUUID: str = Field(..., description="Target message UUID.")
    Status: str = Field(..., description="New status: queued, sent, delivered, failed, undelivered.")
    ErrorCode: Optional[str] = Field(default=None, description="Provider error code if failed.")
    ParentMessageUUID: Optional[str] = Field(default=None)


class WebhookAckResponse(BaseModel):
    """Standard immediate acknowledgement response for webhooks."""
    status: str = "received"
    message_uuid: str
    idempotent_skip: bool = False
