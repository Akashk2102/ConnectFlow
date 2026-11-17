import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.workflow_action import WorkflowAction
from app.services.ai.mock_llm import MockLLMClient
from app.services.messaging.mock_client import MockMessagingClient
from app.services.workflow_orchestrator import WorkflowOrchestrator


@pytest.mark.asyncio
async def test_e2e_safe_order_inquiry_flow(db_session: AsyncSession, test_business: BusinessAccount):
    # Setup Customer & Conversation
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155551042",
        name="Barry Allen",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.flush()

    inbound = Message(
        conversation_id=conv.id,
        direction="inbound",
        sender=customer.phone_number,
        recipient="+18005550199",
        content="Where is my package for order ORD-1042?",
        provider_message_id="msg_e2e_order_01",
        status="received",
    )
    db_session.add(inbound)
    await db_session.commit()

    llm = MockLLMClient()
    messaging = MockMessagingClient()
    messaging.clear()

    orchestrator = WorkflowOrchestrator(db=db_session, llm_client=llm, messaging_client=messaging)
    outbound = await orchestrator.process_inbound_message(inbound.id)

    # 1. Outbound message created
    assert outbound is not None
    assert outbound.direction == "outbound"
    assert outbound.recipient == customer.phone_number
    assert "ORD-1042" in outbound.content
    assert "FedEx" in outbound.content

    # 2. Tool executed
    action_stmt = select(WorkflowAction).where(WorkflowAction.conversation_id == conv.id)
    action = (await db_session.execute(action_stmt)).scalar_one()
    assert action.action_type == "fetch_order_status"
    assert action.status == "executed"
    assert action.requires_human_approval is False

    # 3. Messaging provider transmitted message
    assert len(messaging.sent_messages) == 1
    assert messaging.sent_messages[0]["recipient"] == customer.phone_number


@pytest.mark.asyncio
async def test_e2e_sensitive_refund_gated_flow(db_session: AsyncSession, test_business: BusinessAccount):
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155559921",
        name="Arthur Curry",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.flush()

    inbound = Message(
        conversation_id=conv.id,
        direction="inbound",
        sender=customer.phone_number,
        recipient="+18005550199",
        content="This order ORD-9921 is broken! I demand a full refund and money back!",
        provider_message_id="msg_e2e_refund_01",
        status="received",
    )
    db_session.add(inbound)
    await db_session.commit()

    llm = MockLLMClient()
    messaging = MockMessagingClient()
    messaging.clear()

    orchestrator = WorkflowOrchestrator(db=db_session, llm_client=llm, messaging_client=messaging)
    outbound = await orchestrator.process_inbound_message(inbound.id)

    # 1. Outbound holding message sent
    assert outbound is not None
    assert "supervisor review" in outbound.content

    # 2. Sensitive action created in pending_approval state
    action_stmt = select(WorkflowAction).where(WorkflowAction.conversation_id == conv.id)
    action = (await db_session.execute(action_stmt)).scalar_one()
    assert action.action_type == "issue_refund"
    assert action.status == "pending_approval"
    assert action.requires_human_approval is True

    # 3. Conversation paused in pending_human state
    await db_session.refresh(conv)
    assert conv.status == "pending_human"


@pytest.mark.asyncio
async def test_e2e_faq_direct_response_flow(db_session: AsyncSession, test_business: BusinessAccount):
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155553311",
        name="Victor Stone",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.flush()

    inbound = Message(
        conversation_id=conv.id,
        direction="inbound",
        sender=customer.phone_number,
        recipient="+18005550199",
        content="Hi! What are your business hours?",
        provider_message_id="msg_e2e_faq_01",
        status="received",
    )
    db_session.add(inbound)
    await db_session.commit()

    llm = MockLLMClient()
    messaging = MockMessagingClient()

    orchestrator = WorkflowOrchestrator(db=db_session, llm_client=llm, messaging_client=messaging)
    outbound = await orchestrator.process_inbound_message(inbound.id)

    assert outbound is not None
    assert "ConnectFlow is open" in outbound.content

    # No tool action needed for generic FAQ
    action_stmt = select(WorkflowAction).where(WorkflowAction.conversation_id == conv.id)
    actions = (await db_session.execute(action_stmt)).scalars().all()
    assert len(actions) == 0
