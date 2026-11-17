import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_business
from app.db.session import get_db
from app.models.business_account import BusinessAccount
from app.models.ticket import Ticket

router = APIRouter(tags=["Admin Dashboard & UI"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="ConnectFlow Mission Control Web Dashboard",
    include_in_schema=False,
)
async def serve_dashboard():
    """Serves the interactive operations dashboard SPA."""
    html_path = TEMPLATES_DIR / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse("<h3>Dashboard template not found</h3>", status_code=500)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content, status_code=200)


@router.get(
    "/tickets",
    summary="List customer support tickets",
    description="Returns support tickets created by AI workflows or human agents.",
)
async def list_tickets(
    status_filter: str = Query(None, alias="status", description="Filter by status: open, in_progress, resolved"),
    limit: int = Query(default=50, ge=1, le=100),
    business: BusinessAccount = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    stmt = select(Ticket).where(Ticket.business_id == business.id)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)

    stmt = stmt.order_by(Ticket.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    tickets = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "customer_id": str(t.customer_id),
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]
