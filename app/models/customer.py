import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business_account import BusinessAccount
    from app.models.conversation import Conversation
    from app.models.ticket import Ticket


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an end-user customer communicating with a business."""
    __tablename__ = "customers"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    business: Mapped["BusinessAccount"] = relationship("BusinessAccount", back_populates="customers")
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="customer", cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="customer", cascade="all, delete-orphan"
    )
