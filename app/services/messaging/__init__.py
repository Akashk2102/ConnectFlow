from functools import lru_cache
from fastapi import Depends
from app.core.config import Settings, get_settings
from app.services.messaging.base import MessagingClient, OutboundDeliveryResult
from app.services.messaging.mock_client import MockMessagingClient
from app.services.messaging.plivo_client import PlivoMessagingClient

_global_mock_client = MockMessagingClient()


def get_messaging_client(settings: Settings = Depends(get_settings)) -> MessagingClient:
    """
    Dependency provider that yields the appropriate messaging client adapter.
    Uses MockMessagingClient if credentials are absent or start with 'mock_',
    otherwise activates the production PlivoMessagingClient.
    """
    auth_id = settings.PLIVO_AUTH_ID.strip()
    auth_token = settings.PLIVO_AUTH_TOKEN.strip()

    is_mock = (
        not auth_id
        or not auth_token
        or auth_id.startswith("mock_")
        or settings.APP_ENV in ("testing", "test")
    )

    if is_mock:
        return _global_mock_client

    return PlivoMessagingClient(
        auth_id=auth_id,
        auth_token=auth_token,
        default_sender=settings.PLIVO_PHONE_NUMBER or "+18005550199",
    )


__all__ = [
    "MessagingClient",
    "OutboundDeliveryResult",
    "MockMessagingClient",
    "PlivoMessagingClient",
    "get_messaging_client",
    "_global_mock_client",
]
