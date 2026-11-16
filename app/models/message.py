import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.ai_classification import AIClassification


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a single message sent or received in a conversation."""
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound, outbound
    sender: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received", nullable=False)  # received, queued, sent, delivered, failed

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    classification: Mapped[Optional["AIClassification"]] = relationship(
        "AIClassification", back_populates="message", uselist=False, cascade="all, delete-orphan"
    )
