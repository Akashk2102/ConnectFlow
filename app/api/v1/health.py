from fastapi import APIRouter, Depends, status
from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the operational status, current environment, and timestamp.",
)
async def check_health(
    settings: Settings = Depends(get_settings)
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version="1.0.0"
    )
