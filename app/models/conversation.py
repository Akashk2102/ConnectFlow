import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.message import Message
    from app.models.workflow_action import WorkflowAction


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an ongoing interaction thread with a customer."""
    __tablename__ = "conversations"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), default="sms", nullable=False)  # sms, whatsapp, web
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, resolved, pending_human

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    workflow_actions: Mapped[List["WorkflowAction"]] = relationship(
        "WorkflowAction", back_populates="conversation", cascade="all, delete-orphan"
    )
