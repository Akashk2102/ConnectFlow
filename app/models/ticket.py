import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business_account import BusinessAccount
    from app.models.customer import Customer


class Ticket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a customer support ticket."""
    __tablename__ = "tickets"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)  # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)  # low, medium, high, urgent

    # Relationships
    business: Mapped["BusinessAccount"] = relationship("BusinessAccount", back_populates="tickets")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="tickets")
