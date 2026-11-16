import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root welcome endpoint returns 200 and expected metadata."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "health_check" in data


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Test the /api/v1/health endpoint returns 'ok' and application status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == "ConnectFlow"
        assert data["environment"] == "development"
        assert "timestamp" in data
