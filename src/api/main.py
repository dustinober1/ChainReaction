"""
FastAPI Main Application.

Entry point for the ChainReaction REST API.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog

from src.api.schemas import APIResponse, HealthResponse

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ChainReaction API")
    yield
    logger.info("Shutting down ChainReaction API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from src.api.routes import router as main_router
    from src.api.webhooks_routes import router as webhook_router
    from src.api.routes_v2 import router as v2_router

    app = FastAPI(
        title="ChainReaction API",
        description="Supply Chain Risk Monitoring and Analysis API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation error",
                "message": str(exc),
                "data": None,
                "meta": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "data": None,
                "meta": {},
            },
        )

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Check API health status."""
        from src.config import get_settings
        settings = get_settings()
        
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.now(timezone.utc),
            services={
                "api": "running",
                "database": "not_configured",
                "monitoring": "active",
                "llm_provider": settings.llm_provider.value,
                "llm_model": settings.current_model,
            },
        )

    # LLM status endpoint
    @app.get("/llm/status", tags=["llm"])
    async def llm_status():
        """Check LLM provider status and availability."""
        from src.llm import check_llm_availability
        
        status_info = await check_llm_availability()
        
        return APIResponse(
            success=status_info["available"],
            data=status_info,
            message="LLM provider status retrieved",
        )

    # Root endpoint
    @app.get("/", response_model=APIResponse[dict[str, str]], tags=["root"])
    async def root():
        """API root endpoint."""
        return APIResponse(
            success=True,
            data={
                "name": "ChainReaction API",
                "version": "0.1.0",
                "docs": "/docs",
            },
            message="Welcome to ChainReaction Supply Chain Risk Monitoring API",
        )

    # Include routers
    app.include_router(main_router, prefix="/api/v1")
    app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["webhooks"])
    app.include_router(v2_router, prefix="/api/v2")

    return app


# Create the application instance lazily
_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get or create the FastAPI application."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


# For direct import, create app (deferred)
app = create_app()
