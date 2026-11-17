import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.ai_classification import AIClassification
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.workflow_action import WorkflowAction
from app.schemas.ai import IntentCategory, LLMClassificationResult
from app.services.ai.base import LLMClient
from app.services.messaging.base import MessagingClient
from app.services.tools.executor import dispatch_tool_action, tool_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowOrchestrator:
    """
    Core orchestrator coordinating LLM intelligence, tool execution,
    human approval gating, and outbound messaging responses.
    """

    def __init__(self, db: AsyncSession, llm_client: LLMClient, messaging_client: MessagingClient):
        self.db = db
        self.llm = llm_client
        self.messaging = messaging_client

    async def process_inbound_message(self, message_id: uuid.UUID) -> Optional[Message]:
        """
        Executes the complete autonomous workflow for an inbound message:
        1. Classifies intent & extracts entities.
        2. Routes to approved tools or human approval gate.
        3. Generates contextual response.
        4. Sends outbound response to customer.
        """
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.conversation).selectinload(Conversation.customer),
                selectinload(Message.classification),
            )
        )
        result = await self.db.execute(stmt)
        inbound_msg = result.scalar_one_or_none()

        if not inbound_msg:
            logger.error(f"Message {message_id} not found for workflow orchestration.")
            return None

        conversation = inbound_msg.conversation
        customer = conversation.customer

        # 1. AI Intent Classification & Entity Extraction
        analysis: LLMClassificationResult = await self.llm.classify_message(
            message_text=inbound_msg.content,
            customer_name=customer.name,
        )

        # Record AI classification in DB
        classification_record = AIClassification(
            message_id=inbound_msg.id,
            intent=analysis.intent.value,
            sentiment=analysis.sentiment.value,
            extracted_entities=analysis.extracted_entities,
            confidence_score=analysis.confidence_score,
        )
        self.db.add(classification_record)
        await self.db.flush()

        response_text = ""

        # 2. Tool Routing & Execution
        if analysis.requires_tool and analysis.suggested_tool:
            tool = tool_registry.get(analysis.suggested_tool)

            if tool:
                # Prepare payload based on extracted entities
                payload = dict(analysis.extracted_entities)

                # Supply defaults if required by specific tool schemas
                if tool.name == "issue_refund":
                    payload.setdefault("order_id", payload.get("order_id", "ORD-UNKNOWN"))
                    payload.setdefault("amount", 50.00)
                    payload.setdefault("reason", f"Customer requested refund: {inbound_msg.content[:100]}")
                elif tool.name == "create_support_ticket":
                    payload.setdefault("title", f"Support Request from {customer.name or customer.phone_number}")
                    payload.setdefault("description", inbound_msg.content)
                    payload.setdefault("priority", "high" if analysis.urgency.value == "high" else "medium")

                # Context with database session and customer metadata
                context = {
                    "business_id": customer.business_id,
                    "customer_id": customer.id,
                    "conversation_id": conversation.id,
                }

                # Dispatch tool action
                action: WorkflowAction = await dispatch_tool_action(
                    conversation_id=conversation.id,
                    tool_name=tool.name,
                    payload=payload,
                    db=self.db,
                    context=context,
                )

                if action.requires_human_approval and action.status == "pending_approval":
                    # Sensitive action: Send holding notification to customer
                    response_text = (
                        f"Hello {customer.name or ''}! I have submitted your {analysis.intent.value.replace('_', ' ')} "
                        f"for supervisor review. A support manager will confirm shortly."
                    ).strip()
                elif action.status == "executed" and action.result:
                    # Safe action: Generate response using retrieved tool data
                    if tool.name == "fetch_order_status":
                        data = action.result
                        response_text = (
                            f"Hi {customer.name or ''}! Your order {data.get('order_id')} is currently "
                            f"{data.get('status')} via {data.get('carrier')} (Tracking: {data.get('tracking_number')}). "
                            f"Estimated delivery: {data.get('estimated_delivery')}."
                        ).strip()
                    elif tool.name == "create_support_ticket":
                        response_text = (
                            f"Your support ticket #{action.result.get('ticket_id', '')[:8]} has been created. "
                            f"Our team will follow up with you shortly."
                        )

        # Fallback to direct conversational response if no tool was executed
        if not response_text:
            response_text = analysis.suggested_reply or (
                "Thank you for contacting us. A team member will assist you shortly."
            )

        # 3. Dispatch Outbound Response via Messaging Client
        sender_phone = settings.PLIVO_PHONE_NUMBER or "+18005550199"
        delivery_res = await self.messaging.send_message(
            recipient=customer.phone_number,
            content=response_text,
            sender=sender_phone,
        )

        provider_uuid = (
            delivery_res.message_uuids[0]
            if delivery_res.message_uuids
            else f"out_{uuid.uuid4().hex[:16]}"
        )

        outbound_msg = Message(
            conversation_id=conversation.id,
            direction="outbound",
            sender=sender_phone,
            recipient=customer.phone_number,
            content=response_text,
            provider_message_id=provider_uuid,
            status=delivery_res.status if delivery_res.success else "failed",
        )
        self.db.add(outbound_msg)
        await self.db.commit()
        await self.db.refresh(outbound_msg)

        logger.info(f"Outbound response {outbound_msg.id} dispatched to {customer.phone_number}.")
        return outbound_msg
