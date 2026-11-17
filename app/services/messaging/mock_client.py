import uuid
from typing import Dict, List, Optional
from app.services.messaging.base import MessagingClient, OutboundDeliveryResult


class MockMessagingClient(MessagingClient):
    """
    In-memory telecom provider simulator for testing and local development.
    Requires zero credentials, costs $0, and tracks all sent messages for verification.
    """

    def __init__(self, default_sender: str = "+18005550199"):
        self.default_sender = default_sender
        self.sent_messages: List[Dict] = []
        self.should_fail: bool = False
        self.failure_error: str = "Simulated network timeout"

    async def send_message(
        self,
        recipient: str,
        content: str,
        sender: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> OutboundDeliveryResult:
        if self.should_fail:
            return OutboundDeliveryResult(
                success=False,
                provider_name="mock",
                message_uuids=[],
                status="failed",
                error_message=self.failure_error,
                raw_response={"error": self.failure_error},
            )

        simulated_uuid = f"mock_{uuid.uuid4().hex}"
        record = {
            "message_uuid": simulated_uuid,
            "sender": sender or self.default_sender,
            "recipient": recipient,
            "content": content,
            "callback_url": callback_url,
            "status": "queued",
        }
        self.sent_messages.append(record)

        return OutboundDeliveryResult(
            success=True,
            provider_name="mock",
            message_uuids=[simulated_uuid],
            status="queued",
            raw_response={"message": "message(s) queued", "message_uuid": [simulated_uuid]},
        )

    def clear(self):
        self.sent_messages.clear()
        self.should_fail = False
