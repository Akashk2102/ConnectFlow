import pytest
from httpx import AsyncClient
from app.core.config import get_settings
from app.models.business_account import BusinessAccount
from app.services.webhook_verifier import WebhookSignatureVerifier

settings = get_settings()


@pytest.mark.asyncio
async def test_webhook_signature_verification_success_and_failure(client: AsyncClient, test_business: BusinessAccount):
    """Test cryptographic HMAC-SHA256 signature verification."""
    auth_token = "secret_auth_token_for_plivo_123"
    url = "http://test/api/v1/webhooks/inbound"
    payload = {
        "From": "+14155551111",
        "To": "+18005550199",
        "Text": "Testing signature validation",
        "MessageUUID": "msg_sig_test_001",
        "Type": "sms",
        "Units": 1,
    }

    # 1. Generate valid HMAC-SHA256 signature
    valid_sig = WebhookSignatureVerifier.compute_signature(
        url=url,
        params=payload,
        auth_token=auth_token,
    )

    # 2. Tampered signature should fail
    assert not WebhookSignatureVerifier.verify_signature(
        url=url,
        params=payload,
        auth_token=auth_token,
        signature="invalid_tampered_signature_string",
    )

    # 3. Valid signature must pass
    assert WebhookSignatureVerifier.verify_signature(
        url=url,
        params=payload,
        auth_token=auth_token,
        signature=valid_sig,
    )


@pytest.mark.asyncio
async def test_inbound_webhook_and_idempotency(client: AsyncClient, test_business: BusinessAccount):
    """Test message ingestion, auto-threading, and duplicate webhook idempotency."""
    payload = {
        "From": "+14155557788",
        "To": "+18005550199",
        "Text": "Hi, I have a question about my order #ORD-500",
        "MessageUUID": "msg_unique_uuid_9999",
        "Type": "sms",
        "Units": 1,
    }

    # 1. First delivery of webhook (use bypass header in dev/test)
    response1 = await client.post(
        "/api/v1/webhooks/inbound",
        json=payload,
        headers={"X-Bypass-Signature": "true"},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["status"] == "received"
    assert data1["message_uuid"] == payload["MessageUUID"]
    assert data1["idempotent_skip"] is False

    # 2. Second delivery of the identical webhook (duplicate retry from provider)
    response2 = await client.post(
        "/api/v1/webhooks/inbound",
        json=payload,
        headers={"X-Bypass-Signature": "true"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    # Must identify as duplicate and skip duplicate DB insertion
    assert data2["status"] == "already_processed"
    assert data2["idempotent_skip"] is True


@pytest.mark.asyncio
async def test_delivery_status_report(client: AsyncClient, test_business: BusinessAccount):
    """Test webhook delivery callback updates message status."""
    message_uuid = "msg_delivery_test_42"

    # Ingest message
    await client.post(
        "/api/v1/webhooks/inbound",
        json={
            "From": "+14155553333",
            "To": "+18005550199",
            "Text": "Testing status callback",
            "MessageUUID": message_uuid,
            "Type": "sms",
            "Units": 1,
        },
        headers={"X-Bypass-Signature": "true"},
    )

    # Send delivery receipt callback
    callback_payload = {
        "MessageUUID": message_uuid,
        "Status": "delivered",
    }
    report_res = await client.post(
        "/api/v1/webhooks/delivery-report",
        json=callback_payload,
    )
    assert report_res.status_code == 200
    assert report_res.json()["status"] == "updated"
