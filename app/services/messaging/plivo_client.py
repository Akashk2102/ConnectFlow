import logging
from typing import Optional
import httpx
from app.services.messaging.base import MessagingClient, OutboundDeliveryResult

logger = logging.getLogger(__name__)


class PlivoMessagingClient(MessagingClient):
    """
    Official Plivo REST API Client.
    Follows Plivo's official Message API specification using asynchronous HTTPS requests.
    """

    def __init__(
        self,
        auth_id: str,
        auth_token: str,
        default_sender: str,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = 10.0,
    ):
        self.auth_id = auth_id
        self.auth_token = auth_token
        self.default_sender = default_sender
        self.base_url = f"https://api.plivo.com/v1/Account/{auth_id}/Message/"
        self._custom_client = http_client
        self.timeout = timeout

    async def send_message(
        self,
        recipient: str,
        content: str,
        sender: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> OutboundDeliveryResult:
        src = sender or self.default_sender
        payload = {
            "src": src,
            "dst": recipient,
            "text": content,
        }
        if callback_url:
            payload["url"] = callback_url
            payload["method"] = "POST"

        auth = (self.auth_id, self.auth_token)

        try:
            if self._custom_client:
                response = await self._custom_client.post(
                    self.base_url,
                    json=payload,
                    auth=auth,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        auth=auth,
                    )

            data = response.json() if response.content else {}

            if response.status_code in (200, 202):
                uuids = data.get("message_uuid", [])
                return OutboundDeliveryResult(
                    success=True,
                    provider_name="plivo",
                    message_uuids=uuids if isinstance(uuids, list) else [str(uuids)],
                    status="queued",
                    raw_response=data,
                )
            else:
                error_msg = data.get("error", f"HTTP {response.status_code}: {response.text}")
                logger.error(f"Plivo API Error: {error_msg}")
                return OutboundDeliveryResult(
                    success=False,
                    provider_name="plivo",
                    message_uuids=[],
                    status="failed",
                    error_message=error_msg,
                    raw_response=data,
                )

        except httpx.TimeoutException as exc:
            logger.error(f"Plivo API request timed out: {exc}")
            return OutboundDeliveryResult(
                success=False,
                provider_name="plivo",
                message_uuids=[],
                status="failed",
                error_message="Network request to Plivo timed out.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error communicating with Plivo: {exc}")
            return OutboundDeliveryResult(
                success=False,
                provider_name="plivo",
                message_uuids=[],
                status="failed",
                error_message=str(exc),
            )
