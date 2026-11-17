import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import get_current_business
from app.db.session import get_db
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.messaging import MessagingClient, get_messaging_client

router = APIRouter(tags=["Messaging & Conversations"])
settings = get_settings()


@router.post(
    "/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send outbound message to customer",
    description="Dispatches an outbound SMS/WhatsApp message via the configured messaging provider (Plivo/Mock).",
)
async def send_message(
    payload: MessageCreate,
    business: BusinessAccount = Depends(get_current_business),
    messaging_client: MessagingClient = Depends(get_messaging_client),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    # 1. Resolve or create customer under this business
    customer_stmt = select(Customer).where(
        Customer.business_id == business.id,
        Customer.phone_number == payload.recipient,
    )
    result = await db.execute(customer_stmt)
    customer = result.scalar_one_or_none()

    if not customer:
        customer = Customer(
            business_id=business.id,
            phone_number=payload.recipient,
            name="Unknown",
        )
        db.add(customer)
        await db.flush()

    # 2. Resolve or create conversation
    if payload.conversation_id:
        conv_stmt = select(Conversation).where(
            Conversation.id == payload.conversation_id,
            Conversation.customer_id == customer.id,
        )
        conv_res = await db.execute(conv_stmt)
        conversation = conv_res.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified conversation_id not found for this customer.",
            )
    else:
        conv_stmt = (
            select(Conversation)
            .where(
                Conversation.customer_id == customer.id,
                Conversation.channel == payload.channel,
                Conversation.status == "active",
            )
            .order_by(Conversation.updated_at.desc())
        )
        conv_res = await db.execute(conv_stmt)
        conversation = conv_res.scalars().first()

        if not conversation:
            conversation = Conversation(
                customer_id=customer.id,
                channel=payload.channel,
                status="active",
            )
            db.add(conversation)
            await db.flush()

    # 3. Dispatch to Telecom Provider Adapter (Plivo or Mock)
    sender_number = settings.PLIVO_PHONE_NUMBER or "+18005550199"
    delivery_result = await messaging_client.send_message(
        recipient=customer.phone_number,
        content=payload.content,
        sender=sender_number,
    )

    provider_msg_id = (
        delivery_result.message_uuids[0]
        if delivery_result.message_uuids
        else f"local_{uuid.uuid4().hex[:16]}"
    )
    msg_status = delivery_result.status if delivery_result.success else "failed"

    # 4. Save outbound message record
    message = Message(
        conversation_id=conversation.id,
        direction="outbound",
        sender=sender_number,
        recipient=customer.phone_number,
        content=payload.content,
        provider_message_id=provider_msg_id,
        status=msg_status,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageResponse.model_validate(message)


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List conversations for authenticated business",
)
async def list_conversations(
    channel: str = Query(None, description="Filter by channel: sms, whatsapp"),
    status_filter: str = Query(None, alias="status", description="Filter by status: active, resolved"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    stmt = (
        select(Conversation)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(Customer.business_id == business.id)
    )

    if channel:
        stmt = stmt.where(Conversation.channel == channel)
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)

    stmt = stmt.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation history transcript",
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    stmt = (
        select(Conversation)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            Conversation.id == conversation_id,
            Customer.business_id == business.id,
        )
        .options(selectinload(Conversation.messages))
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return ConversationDetailResponse.model_validate(conversation)
