import uuid
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.message import Message


class AIClassification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents the LLM-derived analysis of an inbound message."""
    __tablename__ = "ai_classifications"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    intent: Mapped[str] = mapped_column(String(64), nullable=False)  # order_inquiry, refund_request, support, general
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)  # positive, neutral, negative
    extracted_entities: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="classification")
