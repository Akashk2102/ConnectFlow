import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.workflow_action import WorkflowAction
from app.models.ticket import Ticket
from app.services.tools.executor import dispatch_tool_action


@pytest.mark.asyncio
async def test_safe_tool_immediate_execution(db_session: AsyncSession, test_business: BusinessAccount):
    # Setup Customer & Conversation
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155556666",
        name="Bruce Wayne",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.commit()

    # Dispatch Safe Tool: fetch_order_status
    action = await dispatch_tool_action(
        conversation_id=conv.id,
        tool_name="fetch_order_status",
        payload={"order_id": "ORD-1042"},
        db=db_session,
    )

    assert action.status == "executed"
    assert action.requires_human_approval is False
    assert action.result["status"] == "in_transit"
    assert action.result["carrier"] == "FedEx"


@pytest.mark.asyncio
async def test_create_ticket_tool_execution(db_session: AsyncSession, test_business: BusinessAccount):
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155557777",
        name="Clark Kent",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.commit()

    # Dispatch: create_support_ticket
    action = await dispatch_tool_action(
        conversation_id=conv.id,
        tool_name="create_support_ticket",
        payload={
            "title": "Broken Charging Cable",
            "description": "Cable frayed on arrival.",
            "priority": "high",
        },
        db=db_session,
        context={"business_id": test_business.id, "customer_id": customer.id},
    )

    assert action.status == "executed"
    assert "ticket_id" in action.result

    # Verify ticket row created in DB
    ticket_stmt = select(Ticket).where(Ticket.business_id == test_business.id)
    ticket = (await db_session.execute(ticket_stmt)).scalar_one()
    assert ticket.title == "Broken Charging Cable"
    assert ticket.priority == "high"


@pytest.mark.asyncio
async def test_sensitive_tool_human_approval_lifecycle(
    client: AsyncClient, db_session: AsyncSession, test_business: BusinessAccount
):
    headers = {"X-API-Key": test_business.api_key}

    # Setup Customer & Conversation
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155558888",
        name="Peter Parker",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.commit()

    # 1. Dispatch Sensitive Tool: issue_refund
    action = await dispatch_tool_action(
        conversation_id=conv.id,
        tool_name="issue_refund",
        payload={"order_id": "ORD-9900", "amount": 75.50, "reason": "Late delivery"},
        db=db_session,
    )

    # Must be gated in pending_approval state
    assert action.status == "pending_approval"
    assert action.requires_human_approval is True
    assert action.result is None

    # Verify conversation status was changed to pending_human
    await db_session.refresh(conv)
    assert conv.status == "pending_human"

    # 2. View Pending Approvals API
    pending_res = await client.get("/api/v1/workflow/actions/pending", headers=headers)
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    assert len(pending_list) >= 1
    assert any(a["id"] == str(action.id) for a in pending_list)

    # 3. Manager Approves Action
    approve_res = await client.post(
        f"/api/v1/workflow/actions/{action.id}/approve",
        json={"approved_by": "manager@store.com"},
        headers=headers,
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "executed"
    assert approved_data["approved_by"] == "manager@store.com"
    assert approved_data["result"]["status"] == "succeeded"

    # Verify conversation is active again
    await db_session.refresh(conv)
    assert conv.status == "active"


@pytest.mark.asyncio
async def test_sensitive_tool_human_rejection(
    client: AsyncClient, db_session: AsyncSession, test_business: BusinessAccount
):
    headers = {"X-API-Key": test_business.api_key}

    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155559999",
        name="Tony Stark",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.commit()

    # Dispatch sensitive tool
    action = await dispatch_tool_action(
        conversation_id=conv.id,
        tool_name="issue_refund",
        payload={"order_id": "ORD-1111", "amount": 500.00, "reason": "Changed mind"},
        db=db_session,
    )

    # Manager Rejects Action
    reject_res = await client.post(
        f"/api/v1/workflow/actions/{action.id}/reject",
        json={"reason": "Outside 30-day return policy", "rejected_by": "lead@store.com"},
        headers=headers,
    )
    assert reject_res.status_code == 200
    rejected_data = reject_res.json()
    assert rejected_data["status"] == "rejected"
    assert "Outside 30-day return policy" in rejected_data["error_message"]
