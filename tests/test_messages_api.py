import pytest
from httpx import AsyncClient
from app.models.business_account import BusinessAccount


@pytest.mark.asyncio
async def test_send_message_and_transcript_flow(
    client: AsyncClient, test_business: BusinessAccount
):
    """Test outbound message creation, conversation auto-threading, and transcript retrieval."""
    headers = {"X-API-Key": test_business.api_key}

    # 1. Send first outbound message to a new recipient
    payload = {
        "recipient": "+14155559876",
        "content": "Hello! Your package has been picked up by the courier.",
        "channel": "sms",
    }
    send_res = await client.post("/api/v1/messages", json=payload, headers=headers)
    assert send_res.status_code == 201
    msg1 = send_res.json()
    assert msg1["direction"] == "outbound"
    assert msg1["status"] == "sent"
    conv_id = msg1["conversation_id"]

    # 2. Send follow-up message to the same recipient (should thread into the same conversation)
    payload_followup = {
        "recipient": "+14155559876",
        "content": "Tracking number: TRK-99283.",
        "channel": "sms",
    }
    followup_res = await client.post(
        "/api/v1/messages", json=payload_followup, headers=headers
    )
    assert followup_res.status_code == 201
    msg2 = followup_res.json()
    assert msg2["conversation_id"] == conv_id

    # 3. List conversations
    conv_list_res = await client.get("/api/v1/conversations", headers=headers)
    assert conv_list_res.status_code == 200
    conversations = conv_list_res.json()
    assert len(conversations) == 1
    assert conversations[0]["id"] == conv_id

    # 4. Get full conversation transcript
    transcript_res = await client.get(
        f"/api/v1/conversations/{conv_id}/messages", headers=headers
    )
    assert transcript_res.status_code == 200
    transcript = transcript_res.json()
    assert transcript["id"] == conv_id
    assert len(transcript["messages"]) == 2
    assert transcript["messages"][0]["content"] == payload["content"]
    assert transcript["messages"][1]["content"] == payload_followup["content"]
