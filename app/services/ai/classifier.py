import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_classification import AIClassification
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.services.ai.base import LLMClient

logger = logging.getLogger(__name__)


async def classify_and_persist_message(
    message_id: uuid.UUID,
    db: AsyncSession,
    llm_client: LLMClient,
) -> Optional[AIClassification]:
    """
    Fetches an inbound message, classifies its intent and entities via the LLM,
    and persists an AIClassification record in the database.
    """
    stmt = (
        select(Message)
        .where(Message.id == message_id)
        .options(
            selectinload(Message.conversation).selectinload(Conversation.customer),
            selectinload(Message.classification),
        )
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        logger.error(f"Message {message_id} not found for AI classification.")
        return None

    if message.classification:
        logger.info(f"Message {message_id} already has AI classification. Skipping.")
        return message.classification

    customer_name = (
        message.conversation.customer.name
        if message.conversation and message.conversation.customer
        else None
    )

    # Execute LLM classification
    analysis = await llm_client.classify_message(
        message_text=message.content,
        customer_name=customer_name,
    )

    # Persist in DB
    classification_record = AIClassification(
        message_id=message.id,
        intent=analysis.intent.value,
        sentiment=analysis.sentiment.value,
        extracted_entities=analysis.extracted_entities,
        confidence_score=analysis.confidence_score,
    )
    db.add(classification_record)
    await db.commit()
    await db.refresh(classification_record)

    logger.info(
        f"Message {message.id} classified as intent='{analysis.intent}' "
        f"(confidence: {analysis.confidence_score:.2f}, sentiment: '{analysis.sentiment}')"
    )
    return classification_record
