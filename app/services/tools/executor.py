import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.workflow_action import WorkflowAction
from app.services.tools.base import BaseTool, ToolResult
from app.services.tools.order_tools import FetchOrderTool
from app.services.tools.refund_tools import IssueRefundTool
from app.services.tools.ticket_tools import CreateSupportTicketTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central catalog of approved, sandboxed backend tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self.register(FetchOrderTool())
        self.register(CreateSupportTicketTool())
        self.register(IssueRefundTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "name": tool.name,
                "description": tool.description,
                "is_sensitive": tool.is_sensitive,
                "schema": tool.parameters_schema.model_json_schema(),
            }
            for name, tool in self._tools.items()
        }


tool_registry = ToolRegistry()


async def dispatch_tool_action(
    conversation_id: uuid.UUID,
    tool_name: str,
    payload: Dict[str, Any],
    db: AsyncSession,
    context: Optional[Dict[str, Any]] = None,
) -> WorkflowAction:
    """
    Validates and executes or gates a tool action.
    Enforces Human-in-the-Loop approval for sensitive operations.
    """
    tool = tool_registry.get(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' is not an approved backend tool.")

    # Validate parameters against Pydantic schema
    validated_params = tool.parameters_schema.model_validate(payload)
    ctx = context or {}
    ctx["db"] = db

    # Check for Human-in-the-Loop sensitivity
    if tool.is_sensitive:
        logger.info(
            f"Action '{tool_name}' is SENSITIVE. Gating execution for human approval on conversation {conversation_id}."
        )
        action = WorkflowAction(
            conversation_id=conversation_id,
            action_type=tool_name,
            status="pending_approval",
            payload=payload,
            requires_human_approval=True,
        )
        db.add(action)

        # Flag conversation as pending human intervention
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await db.execute(conv_stmt)).scalar_one_or_none()
        if conv:
            conv.status = "pending_human"

        await db.commit()
        await db.refresh(action)
        return action

    # Safe tool: Execute immediately
    logger.info(f"Executing safe tool '{tool_name}' on conversation {conversation_id}.")
    result: ToolResult = await tool.execute(validated_params, ctx)

    action = WorkflowAction(
        conversation_id=conversation_id,
        action_type=tool_name,
        status="executed" if result.success else "failed",
        payload=payload,
        result=result.data,
        error_message=result.error_message,
        requires_human_approval=False,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def approve_workflow_action(
    action_id: uuid.UUID,
    approved_by: str,
    db: AsyncSession,
    context: Optional[Dict[str, Any]] = None,
) -> WorkflowAction:
    """
    Approves and executes a gated sensitive action.
    """
    stmt = select(WorkflowAction).where(WorkflowAction.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise ValueError(f"WorkflowAction '{action_id}' not found.")

    if action.status != "pending_approval":
        raise ValueError(f"Action '{action_id}' is not pending approval (current: {action.status}).")

    tool = tool_registry.get(action.action_type)
    if not tool:
        raise ValueError(f"Tool '{action.action_type}' is no longer registered.")

    validated_params = tool.parameters_schema.model_validate(action.payload)
    ctx = context or {}
    ctx["db"] = db

    # Execute now that human approval is verified
    tool_result: ToolResult = await tool.execute(validated_params, ctx)

    action.status = "executed" if tool_result.success else "failed"
    action.approved_by = approved_by
    action.result = tool_result.data
    action.error_message = tool_result.error_message

    # Reset conversation back to active
    conv_stmt = select(Conversation).where(Conversation.id == action.conversation_id)
    conv = (await db.execute(conv_stmt)).scalar_one_or_none()
    if conv and conv.status == "pending_human":
        conv.status = "active"

    await db.commit()
    await db.refresh(action)
    return action


async def reject_workflow_action(
    action_id: uuid.UUID,
    rejected_by: str,
    reason: str,
    db: AsyncSession,
) -> WorkflowAction:
    """
    Rejects a pending sensitive action without executing it.
    """
    stmt = select(WorkflowAction).where(WorkflowAction.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise ValueError(f"WorkflowAction '{action_id}' not found.")

    if action.status != "pending_approval":
        raise ValueError(f"Action '{action_id}' is not pending approval.")

    action.status = "rejected"
    action.approved_by = rejected_by
    action.error_message = f"Rejected by manager: {reason}"

    # Reset conversation
    conv_stmt = select(Conversation).where(Conversation.id == action.conversation_id)
    conv = (await db.execute(conv_stmt)).scalar_one_or_none()
    if conv and conv.status == "pending_human":
        conv.status = "active"

    await db.commit()
    await db.refresh(action)
    return action
