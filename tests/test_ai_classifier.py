import json
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.ai import IntentCategory, Sentiment, Urgency
from app.services.ai.mock_llm import MockLLMClient
from app.services.ai.gemini_llm import GeminiLLMClient
from app.services.ai.classifier import classify_and_persist_message
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ai_classification import AIClassification


@pytest.mark.asyncio
async def test_mock_llm_order_inquiry_intent_and_entity_extraction():
    llm = MockLLMClient()
    result = await llm.classify_message("Where is my package for order ORD-9921? Can you track it?")

    assert result.intent == IntentCategory.ORDER_INQUIRY
    assert result.requires_tool is True
    assert result.suggested_tool == "fetch_order_status"
    assert result.extracted_entities.get("order_id") == "ORD-9921"
    assert result.confidence_score >= 0.90


@pytest.mark.asyncio
async def test_mock_llm_refund_intent_and_sentiment():
    llm = MockLLMClient()
    result = await llm.classify_message("This product is terrible! I want a full refund and money back immediately!")

    assert result.intent == IntentCategory.REFUND_REQUEST
    assert result.sentiment in (Sentiment.NEGATIVE, Sentiment.FRUSTRATED)
    assert result.urgency == Urgency.HIGH
    assert result.requires_tool is True
    assert result.suggested_tool == "issue_refund"


@pytest.mark.asyncio
async def test_mock_llm_support_intent():
    llm = MockLLMClient()
    result = await llm.classify_message("My device has an error code 404 and is defective.")

    assert result.intent == IntentCategory.SUPPORT_TICKET
    assert result.requires_tool is True
    assert result.suggested_tool == "create_support_ticket"


@pytest.mark.asyncio
async def test_mock_llm_faq_intent():
    llm = MockLLMClient()
    result = await llm.classify_message("Hi, what are your business hours on weekends?")

    assert result.intent == IntentCategory.FAQ_GENERAL
    assert result.requires_tool is False
    assert result.suggested_tool is None
    assert "ConnectFlow is open" in result.suggested_reply


@pytest.mark.asyncio
async def test_gemini_client_json_parsing():
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "intent": "order_inquiry",
                                "confidence_score": 0.98,
                                "sentiment": "neutral",
                                "urgency": "medium",
                                "extracted_entities": {"order_id": "ORD-5541"},
                                "requires_tool": True,
                                "suggested_tool": "fetch_order_status",
                                "suggested_reply": "Checking order ORD-5541.",
                            })
                        }
                    ]
                }
            }
        ]
    }

    def handler(request: httpx.Request):
        return httpx.Response(status_code=200, json=mock_gemini_response)

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gemini_client = GeminiLLMClient(
        api_key="mock_gemini_key",
        http_client=mock_http,
    )

    result = await gemini_client.classify_message("Where is ORD-5541?")
    assert result.intent == IntentCategory.ORDER_INQUIRY
    assert result.extracted_entities["order_id"] == "ORD-5541"


@pytest.mark.asyncio
async def test_classify_and_persist_message_flow(db_session: AsyncSession, test_business: BusinessAccount):
    # Setup customer, conversation, message in DB
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155554321",
        name="Diana Prince",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(
        customer_id=customer.id,
        channel="sms",
        status="active",
    )
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        direction="inbound",
        sender=customer.phone_number,
        recipient="+18005550199",
        content="Hello, can you check the shipping on ORD-7788?",
        provider_message_id="msg_ai_test_01",
        status="received",
    )
    db_session.add(msg)
    await db_session.commit()

    # Run classifier
    llm = MockLLMClient()
    classification = await classify_and_persist_message(
        message_id=msg.id,
        db=db_session,
        llm_client=llm,
    )

    assert classification is not None
    assert classification.message_id == msg.id
    assert classification.intent == "order_inquiry"
    assert classification.extracted_entities.get("order_id") == "ORD-7788"

    # Query DB directly to verify persistence
    stmt = select(AIClassification).where(AIClassification.message_id == msg.id)
    persisted = (await db_session.execute(stmt)).scalar_one()
    assert persisted.intent == "order_inquiry"
    assert persisted.confidence_score >= 0.90
