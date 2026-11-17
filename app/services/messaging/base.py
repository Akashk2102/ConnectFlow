from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class OutboundDeliveryResult(BaseModel):
    """Normalized response returned by any messaging provider adapter."""
    success: bool
    provider_name: str
    message_uuids: List[str] = Field(default_factory=list)
    status: str = Field(default="queued", description="Initial status: queued, sent, or failed.")
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class MessagingClient(ABC):
    """
    Abstract interface for messaging providers (Plivo, Mock, etc.).
    Decouples application logic from vendor-specific APIs.
    """

    @abstractmethod
    async def send_message(
        self,
        recipient: str,
        content: str,
        sender: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> OutboundDeliveryResult:
        """
        Sends an SMS/WhatsApp message to a recipient.
        """
        pass
