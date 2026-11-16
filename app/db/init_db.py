from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.base_class import Base
# Import all models so metadata is populated
import app.models  # noqa: F401


async def init_models(engine: AsyncEngine) -> None:
    """Creates all database tables defined in the metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_models(engine: AsyncEngine) -> None:
    """Drops all database tables (used for test teardown)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
