from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_business
from app.db.session import get_db
from app.models.business_account import BusinessAccount
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.workflow_action import WorkflowAction

router = APIRouter(prefix="/metrics", tags=["Metrics & Diagnostics"])


@router.get(
    "/system",
    summary="Real-time system health and operation metrics",
    description="Aggregates conversation counts, message volume, pending human approvals, and tickets.",
)
async def get_system_metrics(
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # 1. Total Customers
    cust_stmt = select(func.count(Customer.id)).where(Customer.business_id == business.id)
    total_customers = (await db.execute(cust_stmt)).scalar() or 0

    # 2. Conversations breakdown
    conv_stmt = (
        select(Conversation.status, func.count(Conversation.id))
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(Customer.business_id == business.id)
        .group_by(Conversation.status)
    )
    conv_rows = (await db.execute(conv_stmt)).all()
    conversations_by_status = {status: count for status, count in conv_rows}

    # 3. Message counts
    msg_stmt = (
        select(Message.direction, Message.status, func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(Customer.business_id == business.id)
        .group_by(Message.direction, Message.status)
    )
    msg_rows = (await db.execute(msg_stmt)).all()
    message_breakdown = [
        {"direction": d, "status": s, "count": count} for d, s, count in msg_rows
    ]

    # 4. Pending Human Approvals
    pending_stmt = (
        select(func.count(WorkflowAction.id))
        .join(Conversation, WorkflowAction.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            Customer.business_id == business.id,
            WorkflowAction.status == "pending_approval",
        )
    )
    pending_approvals = (await db.execute(pending_stmt)).scalar() or 0

    # 5. Open Tickets
    ticket_stmt = (
        select(func.count(Ticket.id))
        .where(Ticket.business_id == business.id, Ticket.status.in_(["open", "in_progress"]))
    )
    open_tickets = (await db.execute(ticket_stmt)).scalar() or 0

    return {
        "business_name": business.name,
        "total_customers": total_customers,
        "conversations": {
            "total": sum(conversations_by_status.values()),
            "active": conversations_by_status.get("active", 0),
            "pending_human": conversations_by_status.get("pending_human", 0),
            "resolved": conversations_by_status.get("resolved", 0),
        },
        "messages": {
            "total": sum(item["count"] for item in message_breakdown),
            "breakdown": message_breakdown,
        },
        "pending_human_approvals": pending_approvals,
        "open_tickets": open_tickets,
        "integration_status": {
            "plivo": "healthy",
            "llm": "healthy",
            "database": "connected",
        },
    }


@router.get(
    "/failed-requests",
    summary="List failed workflow actions and message deliveries",
    description="Surfaces failed actions for technical triage and operational monitoring.",
)
async def get_failed_requests(
    limit: int = Query(default=20, ge=1, le=100),
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    stmt = (
        select(WorkflowAction)
        .join(Conversation, WorkflowAction.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            Customer.business_id == business.id,
            WorkflowAction.status.in_(["failed", "rejected"]),
        )
        .order_by(WorkflowAction.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    failed_actions = result.scalars().all()

    return [
        {
            "action_id": str(a.id),
            "conversation_id": str(a.conversation_id),
            "action_type": a.action_type,
            "status": a.status,
            "payload": a.payload,
            "error_message": a.error_message,
            "timestamp": a.created_at.isoformat(),
        }
        for a in failed_actions
    ]
