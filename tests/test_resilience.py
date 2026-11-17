import pytest
from fastapi import HTTPException, Request
from httpx import AsyncClient
from app.core.resilience import retry_with_backoff
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.workflow_action import WorkflowAction
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_retry_with_backoff_transient_recovery():
    attempts = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01, backoff_factor=1.5, jitter=False)
    async def flaky_network_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Transient network failure")
        return "Success on attempt 3"

    result = await flaky_network_call()
    assert result == "Success on attempt 3"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries_exceeded():
    attempts = 0

    @retry_with_backoff(max_retries=2, base_delay=0.01, backoff_factor=1.0, jitter=False)
    async def permanently_failing_call():
        nonlocal attempts
        attempts += 1
        raise TimeoutError("Endpoint unreachable")

    with pytest.raises(TimeoutError):
        await permanently_failing_call()

    # Initial call + 2 retries = 3 attempts total
    assert attempts == 3


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_enforcement():
    # Allow 2 requests per 5-second window
    limiter = SlidingWindowRateLimiter(requests_limit=2, window_seconds=5)

    class MockRequest:
        headers = {"X-API-Key": "test_client_key"}
        client = None

    mock_req = MockRequest()

    # 1st and 2nd calls should pass without exception
    await limiter(mock_req)
    await limiter(mock_req)

    # 3rd call must trigger HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter(mock_req)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_system_metrics_endpoint(
    client: AsyncClient, db_session: AsyncSession, test_business: BusinessAccount
):
    headers = {"X-API-Key": test_business.api_key}

    # Setup customer and conversation
    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155551212",
        name="Metrics Test User",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.commit()

    res = await client.get("/api/v1/metrics/system", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["business_name"] == test_business.name
    assert data["total_customers"] >= 1
    assert data["conversations"]["total"] >= 1
    assert "integration_status" in data


@pytest.mark.asyncio
async def test_failed_requests_endpoint(
    client: AsyncClient, db_session: AsyncSession, test_business: BusinessAccount
):
    headers = {"X-API-Key": test_business.api_key}

    customer = Customer(
        business_id=test_business.id,
        phone_number="+14155551313",
        name="Failed Actions User",
    )
    db_session.add(customer)
    await db_session.flush()

    conv = Conversation(customer_id=customer.id, channel="sms", status="active")
    db_session.add(conv)
    await db_session.flush()

    failed_action = WorkflowAction(
        conversation_id=conv.id,
        action_type="issue_refund",
        status="failed",
        payload={"order_id": "ORD-FAIL"},
        error_message="Card declined by issuer",
        requires_human_approval=True,
    )
    db_session.add(failed_action)
    await db_session.commit()

    res = await client.get("/api/v1/metrics/failed-requests", headers=headers)
    assert res.status_code == 200
    failed_list = res.json()
    assert len(failed_list) >= 1
    assert failed_list[0]["action_type"] == "issue_refund"
    assert failed_list[0]["error_message"] == "Card declined by issuer"
