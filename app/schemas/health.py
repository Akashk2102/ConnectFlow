from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for service health status response."""
    status: str = Field(default="ok", examples=["ok"])
    app_name: str = Field(..., examples=["ConnectFlow"])
    environment: str = Field(..., examples=["development"])
    version: str = Field(default="1.0.0", examples=["1.0.0"])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
