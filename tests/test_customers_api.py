import pytest
from httpx import AsyncClient
from app.models.business_account import BusinessAccount


@pytest.mark.asyncio
async def test_customer_authentication_required(client: AsyncClient):
    """Calling customer API without X-API-Key must return 401 Unauthorized."""
    response = await client.get("/api/v1/customers")
    assert response.status_code == 401
    assert "Missing 'X-API-Key'" in response.json()["detail"]


@pytest.mark.asyncio
async def test_customer_phone_validation(client: AsyncClient, test_business: BusinessAccount):
    """Invalid phone numbers must be rejected by Pydantic validation with 422."""
    headers = {"X-API-Key": test_business.api_key}
    response = await client.post(
        "/api/v1/customers",
        json={"phone_number": "invalid-phone", "name": "John Doe"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_and_get_customer_flow(client: AsyncClient, test_business: BusinessAccount):
    """Full lifecycle: Create, Read, Update, Search, and Delete customer."""
    headers = {"X-API-Key": test_business.api_key}

    # 1. Create Customer
    payload = {
        "phone_number": "+14155552671",
        "name": "Sarah Connor",
        "email": "sarah@resistance.org",
        "custom_metadata": {"vip": True, "notes": "Prefers SMS"},
    }
    create_res = await client.post("/api/v1/customers", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    customer_id = created_data["id"]
    assert created_data["name"] == "Sarah Connor"
    assert created_data["phone_number"] == "+14155552671"

    # 2. Duplicate Creation should fail with 409
    dup_res = await client.post("/api/v1/customers", json=payload, headers=headers)
    assert dup_res.status_code == 409

    # 3. Get Customer by ID
    get_res = await client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "sarah@resistance.org"

    # 4. Search Customer
    search_res = await client.get("/api/v1/customers?search=Sarah", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1

    # 5. Patch Customer
    patch_res = await client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"name": "Sarah J. Connor", "custom_metadata": {"tier": "platinum"}},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["name"] == "Sarah J. Connor"
    assert updated_data["custom_metadata"]["tier"] == "platinum"

    # 6. Delete Customer
    del_res = await client.delete(f"/api/v1/customers/{customer_id}", headers=headers)
    assert del_res.status_code == 204

    # 7. Verify 404 after deletion
    verify_res = await client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert verify_res.status_code == 404
