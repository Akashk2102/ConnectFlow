from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.customers import router as customers_router
from app.api.v1.messages import router as messages_router

api_router = APIRouter()

# Register sub-routers under /api/v1
api_router.include_router(health_router)
api_router.include_router(customers_router)
api_router.include_router(messages_router)
