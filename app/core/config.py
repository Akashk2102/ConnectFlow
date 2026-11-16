from functools import lru_cache
from typing import Literal, Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings configured via environment variables.
    Pydantic automatically reads values from the environment and falls back to .env
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    APP_NAME: str = "ConnectFlow"
    APP_ENV: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "default_insecure_key_for_dev_only_change_in_production"

    # Server Network Binding
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database Settings
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "connectflow_db"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Computes the async database connection string.
        Prioritizes explicit DATABASE_URL if provided, else constructs PostgreSQL URI.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis Settings (Stage 10)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Plivo Messaging Settings (Stage 6)
    PLIVO_AUTH_ID: str = ""
    PLIVO_AUTH_TOKEN: str = ""
    PLIVO_PHONE_NUMBER: str = ""

    # LLM Service Settings (Stage 7 & 8)
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of the settings."""
    return Settings()
