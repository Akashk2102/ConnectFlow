import json
import pytest
import httpx
from app.services.messaging.mock_client import MockMessagingClient
from app.services.messaging.plivo_client import PlivoMessagingClient
from app.models.business_account import BusinessAccount


@pytest.mark.asyncio
async def test_mock_messaging_client_lifecycle():
    client = MockMessagingClient(default_sender="+18005550199")
    client.clear()

    # 1. Send normal message
    result = await client.send_message(
        recipient="+14155552671",
        content="Your verification code is 849201",
    )
    assert result.success is True
    assert result.status == "queued"
    assert len(result.message_uuids) == 1
    assert len(client.sent_messages) == 1
    assert client.sent_messages[0]["content"] == "Your verification code is 849201"

    # 2. Simulate network failure
    client.should_fail = True
    fail_result = await client.send_message(
        recipient="+14155552671",
        content="This should fail",
    )
    assert fail_result.success is False
    assert fail_result.status == "failed"
    assert "Simulated network timeout" in fail_result.error_message


@pytest.mark.asyncio
async def test_plivo_messaging_client_success_response():
    # Mock transport simulating Plivo's 202 Accepted response
    def handler(request: httpx.Request):
        assert request.method == "POST"
        assert "api.plivo.com" in str(request.url)
        body = json.loads(request.content)
        assert body["dst"] == "+14155552671"
        assert body["text"] == "Hello from Plivo!"

        return httpx.Response(
            status_code=202,
            json={
                "message": "message(s) queued",
                "message_uuid": ["plivo_test_uuid_12345"],
                "api_id": "api_req_999",
            },
        )

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    plivo_client = PlivoMessagingClient(
        auth_id="PLIVO_MOCK_AUTH_ID",
        auth_token="PLIVO_MOCK_AUTH_TOKEN",
        default_sender="+18005550199",
        http_client=mock_http,
    )

    result = await plivo_client.send_message(
        recipient="+14155552671",
        content="Hello from Plivo!",
    )
    assert result.success is True
    assert result.provider_name == "plivo"
    assert result.message_uuids == ["plivo_test_uuid_12345"]
    assert result.status == "queued"


@pytest.mark.asyncio
async def test_plivo_messaging_client_error_response():
    # Mock transport simulating 400 Invalid Destination
    def handler(request: httpx.Request):
        return httpx.Response(
            status_code=400,
            json={"error": "Destination number is not reachable"},
        )

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    plivo_client = PlivoMessagingClient(
        auth_id="PLIVO_MOCK_AUTH_ID",
        auth_token="PLIVO_MOCK_AUTH_TOKEN",
        default_sender="+18005550199",
        http_client=mock_http,
    )

    result = await plivo_client.send_message(
        recipient="+10000000000",
        content="Invalid test",
    )
    assert result.success is False
    assert result.status == "failed"
    assert "Destination number is not reachable" in result.error_message


@pytest.mark.asyncio
async def test_plivo_messaging_client_timeout_handling():
    # Mock transport simulating a timeout exception
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Connection timed out")

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    plivo_client = PlivoMessagingClient(
        auth_id="PLIVO_MOCK_AUTH_ID",
        auth_token="PLIVO_MOCK_AUTH_TOKEN",
        default_sender="+18005550199",
        http_client=mock_http,
    )

    result = await plivo_client.send_message(
        recipient="+14155552671",
        content="Timeout test",
    )
    assert result.success is False
    assert result.status == "failed"
    assert "timed out" in result.error_message.lower()
