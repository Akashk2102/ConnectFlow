import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_business
from app.db.session import get_db
from app.models.business_account import BusinessAccount
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customer Management"])


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer",
    description="Creates a new customer record under the authenticated business account.",
)
async def create_customer(
    payload: CustomerCreate,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    # Check if customer already exists for this business
    existing_stmt = select(Customer).where(
        Customer.business_id == business.id,
        Customer.phone_number == payload.phone_number,
    )
    result = await db.execute(existing_stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Customer with phone number '{payload.phone_number}' already exists.",
        )

    customer = Customer(
        business_id=business.id,
        phone_number=payload.phone_number,
        name=payload.name,
        email=payload.email,
        custom_metadata=payload.custom_metadata,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=List[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="List customers with pagination and search",
)
async def list_customers(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> List[CustomerResponse]:
    stmt = select(Customer).where(Customer.business_id == business.id)

    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            (Customer.name.ilike(search_term))
            | (Customer.phone_number.ilike(search_term))
            | (Customer.email.ilike(search_term))
        )

    stmt = stmt.order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    customers = result.scalars().all()
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer details by ID",
)
async def get_customer(
    customer_id: uuid.UUID,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    stmt = select(Customer).where(
        Customer.id == customer_id,
        Customer.business_id == business.id,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update customer profile or metadata",
)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    stmt = select(Customer).where(
        Customer.id == customer_id,
        Customer.business_id == business.id,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    if payload.name is not None:
        customer.name = payload.name
    if payload.email is not None:
        customer.email = payload.email
    if payload.custom_metadata is not None:
        # Merge or replace metadata
        updated_meta = dict(customer.custom_metadata or {})
        updated_meta.update(payload.custom_metadata)
        customer.custom_metadata = updated_meta

    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a customer",
)
async def delete_customer(
    customer_id: uuid.UUID,
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Customer).where(
        Customer.id == customer_id,
        Customer.business_id == business.id,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    await db.delete(customer)
    await db.commit()
