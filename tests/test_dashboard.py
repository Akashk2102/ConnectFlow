import pytest
from httpx import AsyncClient
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.ticket import Ticket
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_serve_dashboard_page(client: AsyncClient):
    """Test dashboard HTML page is served correctly."""
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "ConnectFlow" in response.text
    assert "<!DOCTYPE html>" in response.text


@pytest.mark.asyncio
async def test_list_tickets_endpoint(
    client: AsyncClient, db_session: AsyncSession, test_business: BusinessAccount
):
    headers = {"X-API-Key": test_business.api_key}

    # Setup customer and ticket
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155551818",
        name="Dashboard Ticket User",
    )
    db_session.add(customer)
    await db_session.flush()

    ticket = Ticket(
        business_id=test_business.id,
        customer_id=customer.id,
        title="Delivery late by 5 days",
        description="Customer has not received package.",
        priority="urgent",
        status="open",
    )
    db_session.add(ticket)
    await db_session.commit()

    res = await client.get("/api/v1/tickets", headers=headers)
    assert res.status_code == 200
    tickets = res.json()
    assert len(tickets) >= 1
    assert tickets[0]["title"] == "Delivery late by 5 days"
    assert tickets[0]["priority"] == "urgent"
