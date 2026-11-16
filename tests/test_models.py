import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.db.base_class import Base
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ai_classification import AIClassification
from app.models.workflow_action import WorkflowAction
from app.models.ticket import Ticket


@pytest.fixture
async def test_session():
    """Provides an isolated in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_business_and_customer(test_session: AsyncSession):
    # 1. Create Business Account
    business = BusinessAccount(
        name="Acme Logistics",
        email="ops@acme.com",
        hashed_password="secure_hashed_password",
        api_key=f"sk_live_{uuid.uuid4().hex}",
    )
    test_session.add(business)
    await test_session.commit()
    await test_session.refresh(business)

    assert business.id is not None
    assert business.is_active is True

    # 2. Create Customer
    customer = Customer(
        business_id=business.id,
        phone_number="+14155552671",
        name="Alice Smith",
        email="alice@example.com",
        custom_metadata={"tier": "vip", "locale": "en_US"},
    )
    test_session.add(customer)
    await test_session.commit()
    await test_session.refresh(customer)

    assert customer.id is not None
    assert customer.business_id == business.id
    assert customer.custom_metadata["tier"] == "vip"


@pytest.mark.asyncio
async def test_conversation_and_ai_classification_lifecycle(test_session: AsyncSession):
    # 1. Setup Business & Customer
    business = BusinessAccount(
        name="ShopNow",
        email="support@shopnow.com",
        hashed_password="pwd",
        api_key="sk_shopnow_123",
    )
    test_session.add(business)
    await test_session.flush()

    customer = Customer(
        business_id=business.id,
        phone_number="+12025550143",
        name="Bob Jones",
    )
    test_session.add(customer)
    await test_session.flush()

    # 2. Create Conversation
    conversation = Conversation(
        customer_id=customer.id,
        channel="sms",
        status="active",
    )
    test_session.add(conversation)
    await test_session.flush()

    # 3. Create Inbound Message
    msg = Message(
        conversation_id=conversation.id,
        direction="inbound",
        sender="+12025550143",
        recipient="+18005551234",
        content="Where is my order #ORD-9876?",
        provider_message_id="plivo_msg_uuid_99",
        status="received",
    )
    test_session.add(msg)
    await test_session.flush()

    # 4. Attach AI Classification
    ai_analysis = AIClassification(
        message_id=msg.id,
        intent="order_inquiry",
        sentiment="neutral",
        extracted_entities={"order_id": "ORD-9876"},
        confidence_score=0.98,
    )
    test_session.add(ai_analysis)

    # 5. Attach Workflow Action (Human-in-the-Loop check)
    action = WorkflowAction(
        conversation_id=conversation.id,
        action_type="fetch_order",
        status="executed",
        payload={"order_id": "ORD-9876"},
        result={"order_status": "in_transit", "eta": "2 days"},
        requires_human_approval=False,
    )
    test_session.add(action)
    await test_session.commit()

    # Verify relationships & queries
    query = select(Message).where(Message.id == msg.id)
    result = await test_session.execute(query)
    stored_msg = result.scalar_one()

    assert stored_msg.content == "Where is my order #ORD-9876?"
    assert stored_msg.provider_message_id == "plivo_msg_uuid_99"


@pytest.mark.asyncio
async def test_ticket_creation(test_session: AsyncSession):
    business = BusinessAccount(
        name="SupportHQ",
        email="help@supporthq.com",
        hashed_password="pwd",
        api_key="sk_supporthq_456",
    )
    test_session.add(business)
    await test_session.flush()

    customer = Customer(
        business_id=business.id,
        phone_number="+13125550188",
        name="Charlie Brown",
    )
    test_session.add(customer)
    await test_session.flush()

    ticket = Ticket(
        business_id=business.id,
        customer_id=customer.id,
        title="Package damaged during transit",
        description="Customer reported broken screen upon delivery.",
        status="open",
        priority="high",
    )
    test_session.add(ticket)
    await test_session.commit()
    await test_session.refresh(ticket)

    assert ticket.id is not None
    assert ticket.status == "open"
    assert ticket.priority == "high"
