import secrets
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.business_account import BusinessAccount

# Standard HTTP Header for API Key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key(prefix: str = "cf_live") -> str:
    """Generates a cryptographically secure random API key."""
    return f"{prefix}_{secrets.token_hex(24)}"


async def get_current_business(
    api_key: Optional[str] = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> BusinessAccount:
    """
    FastAPI security dependency.
    Validates the X-API-Key header against active business accounts in the database.
    Raises HTTP 401 Unauthorized if missing, invalid, or inactive.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-API-Key' header in request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    stmt = select(BusinessAccount).where(BusinessAccount.api_key == api_key)
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key provided.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not business.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business account is suspended or inactive.",
        )

    return business
