import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_business
from app.db.session import get_db
from app.models.business_account import BusinessAccount
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.workflow_action import WorkflowAction
from app.schemas.message import MessageResponse
from app.schemas.workflow import ApproveActionRequest, RejectActionRequest, WorkflowActionResponse
from app.services.ai import get_llm_client
from app.services.messaging import get_messaging_client
from app.services.tools.executor import approve_workflow_action, reject_workflow_action, tool_registry
from app.services.workflow_orchestrator import WorkflowOrchestrator

router = APIRouter(prefix="/workflow", tags=["Workflow & Human Approvals"])


@router.get(
    "/tools",
    summary="List all approved backend tools",
    description="Returns the catalog of sandboxed tools, parameter schemas, and sensitivity levels.",
)
async def list_available_tools(
    business: BusinessAccount = Depends(get_current_business),
) -> Dict[str, Any]:
    return tool_registry.list_tools()


@router.get(
    "/actions/pending",
    response_model=List[WorkflowActionResponse],
    summary="List actions awaiting human approval",
    description="Returns pending sensitive actions (e.g. refunds) that require manager authorization.",
)
async def list_pending_actions(
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> List[WorkflowActionResponse]:
    stmt = (
        select(WorkflowAction)
        .join(Conversation, WorkflowAction.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            Customer.business_id == business.id,
            WorkflowAction.status == "pending_approval",
        )
        .order_by(WorkflowAction.created_at.desc())
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()
    return [WorkflowActionResponse.model_validate(a) for a in actions]


@router.post(
    "/actions/{action_id}/approve",
    response_model=WorkflowActionResponse,
    summary="Approve and execute a gated action",
    description="Authorizes a pending sensitive operation (e.g. refund) to execute.",
)
async def approve_action(
    action_id: uuid.UUID,
    payload: ApproveActionRequest,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> WorkflowActionResponse:
    stmt = (
        select(WorkflowAction)
        .join(Conversation, WorkflowAction.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            WorkflowAction.id == action_id,
            Customer.business_id == business.id,
        )
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or does not belong to your business account.",
        )

    try:
        updated_action = await approve_workflow_action(
            action_id=action.id,
            approved_by=payload.approved_by or business.email,
            db=db,
        )
        return WorkflowActionResponse.model_validate(updated_action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/actions/{action_id}/reject",
    response_model=WorkflowActionResponse,
    summary="Reject a gated action",
    description="Denies a pending sensitive action, recording the reason without executing it.",
)
async def reject_action(
    action_id: uuid.UUID,
    payload: RejectActionRequest,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> WorkflowActionResponse:
    stmt = (
        select(WorkflowAction)
        .join(Conversation, WorkflowAction.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            WorkflowAction.id == action_id,
            Customer.business_id == business.id,
        )
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found.",
        )

    try:
        updated_action = await reject_workflow_action(
            action_id=action.id,
            rejected_by=payload.rejected_by or business.email,
            reason=payload.reason,
            db=db,
        )
        return WorkflowActionResponse.model_validate(updated_action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/process-message/{message_id}",
    response_model=MessageResponse,
    summary="Execute or replay full orchestration on a message",
)
async def process_message_orchestration(
    message_id: uuid.UUID,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
    llm = Depends(get_llm_client),
    messaging = Depends(get_messaging_client),
) -> MessageResponse:
    # Verify message ownership
    stmt = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(
            Message.id == message_id,
            Customer.business_id == business.id,
        )
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Message not found.")

    orchestrator = WorkflowOrchestrator(db=db, llm_client=llm, messaging_client=messaging)
    outbound = await orchestrator.process_inbound_message(message_id)
    if not outbound:
        raise HTTPException(status_code=500, detail="Failed to process orchestration.")
    return MessageResponse.model_validate(outbound)
