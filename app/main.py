from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.core.config import get_settings
from app.api.v1.router import api_router
from app.api.v1.dashboard import serve_dashboard

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager.
    Runs startup logic before yielding, and cleanup logic on shutdown.
    """
    print(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    yield
    print(f"Gracefully shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Customer Communication & Workflow Automation Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Top-level direct dashboard route
@app.get("/dashboard", include_in_schema=False)
async def root_dashboard():
    return await serve_dashboard()


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "documentation": "/docs",
        "dashboard": "/dashboard",
        "api_v1": settings.API_V1_PREFIX,
        "health_check": f"{settings.API_V1_PREFIX}/health"
    }
