import uuid
from typing import Any, Dict
from pydantic import BaseModel, Field
from app.models.ticket import Ticket
from app.services.tools.base import BaseTool, ToolResult


class CreateTicketParams(BaseModel):
    title: str = Field(..., max_length=200, examples=["Defective Screen"])
    description: str = Field(..., examples=["Customer reports monitor does not power on."])
    priority: str = Field(default="medium", examples=["low", "medium", "high", "urgent"])


class CreateSupportTicketTool(BaseTool):
    name = "create_support_ticket"
    description = "Opens a formal support ticket in ConnectFlow for customer service review."
    parameters_schema = CreateTicketParams
    is_sensitive = False

    async def execute(self, params: CreateTicketParams, context: Dict[str, Any]) -> ToolResult:
        db = context.get("db")
        business_id = context.get("business_id")
        customer_id = context.get("customer_id")

        if not db or not business_id or not customer_id:
            return ToolResult(
                success=False,
                tool_name=self.name,
                data={},
                error_message="Missing database session or context IDs.",
            )

        ticket = Ticket(
            business_id=business_id,
            customer_id=customer_id,
            title=params.title,
            description=params.description,
            priority=params.priority,
            status="open",
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

        return ToolResult(
            success=True,
            tool_name=self.name,
            data={
                "ticket_id": str(ticket.id),
                "title": ticket.title,
                "priority": ticket.priority,
                "status": ticket.status,
            },
        )
