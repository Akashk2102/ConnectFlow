import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.db.session import async_session_factory, get_db
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.webhook import DeliveryReportWebhook, InboundMessageWebhook, WebhookAckResponse
from app.services.ai import get_llm_client
from app.services.messaging import get_messaging_client
from app.services.webhook_verifier import WebhookSignatureVerifier
from app.services.workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks & Ingress"])


async def process_inbound_message_background(message_id_str: str):
    """
    Background worker orchestrating the full autonomous communication cycle:
    Inbound -> Intent -> Tool -> Outbound reply.
    """
    try:
        message_id = uuid.UUID(message_id_str)
        async with async_session_factory() as session:
            settings = get_settings()
            llm_client = get_llm_client(settings)
            messaging_client = get_messaging_client(settings)
            orchestrator = WorkflowOrchestrator(
                db=session,
                llm_client=llm_client,
                messaging_client=messaging_client,
            )
            await orchestrator.process_inbound_message(message_id)
    except Exception as exc:
        logger.error(f"Error in background workflow orchestrator: {exc}", exc_info=True)


@router.post(
    "/inbound",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive Inbound Message Webhook",
    description="Processes incoming SMS/WhatsApp messages with signature verification, idempotency, and AI orchestration.",
)
async def handle_inbound_message(
    payload: InboundMessageWebhook,
    background_tasks: BackgroundTasks,
    request: Request,
    x_plivo_signature_v2: str = Header(None, alias="X-Plivo-Signature-V2"),
    x_plivo_signature_v2_nonce: str = Header("", alias="X-Plivo-Signature-V2-Nonce"),
    x_bypass_signature: str = Header(None, alias="X-Bypass-Signature"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookAckResponse:
    # 1. Cryptographic Signature Verification
    should_verify = (
        settings.APP_ENV == "production"
        or (x_plivo_signature_v2 is not None and x_bypass_signature != "true")
    )

    if should_verify:
        url = str(request.url)
        params = payload.model_dump()
        is_valid = WebhookSignatureVerifier.verify_signature(
            url=url,
            params=params,
            auth_token=settings.PLIVO_AUTH_TOKEN,
            signature=x_plivo_signature_v2 or "",
            nonce=x_plivo_signature_v2_nonce,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook cryptographic signature.",
            )

    # 2. Idempotency Check: Defeat duplicate provider retries
    dup_stmt = select(Message).where(Message.provider_message_id == payload.MessageUUID)
    dup_result = await db.execute(dup_stmt)
    existing_message = dup_result.scalar_one_or_none()

    if existing_message:
        return WebhookAckResponse(
            status="already_processed",
            message_uuid=payload.MessageUUID,
            idempotent_skip=True,
        )

    # 3. Locate Target Business Account
    biz_stmt = select(BusinessAccount).where(BusinessAccount.is_active == True).limit(1)  # noqa: E712
    biz_res = await db.execute(biz_stmt)
    business = biz_res.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No active business account configured to receive messages.",
        )

    # 4. Resolve or Register Customer
    cust_stmt = select(Customer).where(
        Customer.business_id == business.id,
        Customer.phone_number == payload.From,
    )
    cust_res = await db.execute(cust_stmt)
    customer = cust_res.scalar_one_or_none()

    if not customer:
        customer = Customer(
            business_id=business.id,
            phone_number=payload.From,
            name="New Inbound Contact",
        )
        db.add(customer)
        await db.flush()

    # 5. Resolve or Create Active Conversation
    conv_stmt = (
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.channel == payload.Type,
            Conversation.status == "active",
        )
        .order_by(Conversation.updated_at.desc())
    )
    conv_res = await db.execute(conv_stmt)
    conversation = conv_res.scalars().first()

    if not conversation:
        conversation = Conversation(
            customer_id=customer.id,
            channel=payload.Type,
            status="active",
        )
        db.add(conversation)
        await db.flush()

    # 6. Store Inbound Message
    message = Message(
        conversation_id=conversation.id,
        direction="inbound",
        sender=payload.From,
        recipient=payload.To,
        content=payload.Text,
        provider_message_id=payload.MessageUUID,
        status="received",
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # 7. Asynchronous Task Dispatch for End-to-End Workflow Orchestration
    background_tasks.add_task(process_inbound_message_background, str(message.id))

    return WebhookAckResponse(
        status="received",
        message_uuid=payload.MessageUUID,
        idempotent_skip=False,
    )


@router.post(
    "/delivery-report",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive Delivery Status Callback",
    description="Updates message status (sent, delivered, failed) when provider delivers receipt.",
)
async def handle_delivery_report(
    payload: DeliveryReportWebhook,
    db: AsyncSession = Depends(get_db),
) -> WebhookAckResponse:
    stmt = select(Message).where(Message.provider_message_id == payload.MessageUUID)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if message:
        status_map = {
            "delivered": "delivered",
            "sent": "sent",
            "queued": "queued",
            "failed": "failed",
            "undelivered": "failed",
        }
        message.status = status_map.get(payload.Status.lower(), message.status)
        await db.commit()

    return WebhookAckResponse(
        status="updated",
        message_uuid=payload.MessageUUID,
        idempotent_skip=False,
    )
