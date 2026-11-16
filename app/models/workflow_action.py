import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class WorkflowAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Represents an action selected by the AI (or user) to execute.
    Supports Human-in-the-Loop review for sensitive operations (e.g. refunds).
    """
    __tablename__ = "workflow_actions"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # fetch_order, create_ticket, issue_refund
    status: Mapped[str] = mapped_column(
        String(32), default="pending_approval", nullable=False
    )  # pending_approval, approved, rejected, executed, failed
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="workflow_actions")
