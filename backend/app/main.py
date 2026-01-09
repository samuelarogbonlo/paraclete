"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from typing import AsyncGenerator

from app.config import settings
from app.db.database import init_db, close_db
from app.core.exceptions import ParacleteException
from app.api.v1.router import api_router
from app.api.websocket import router as websocket_router
from app.mcp.proxy import get_mcp_proxy
from app.services.compute.scheduler import start_vm_scheduler, stop_vm_scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle events.
    """
    # Startup
    logger.info("Starting Paraclete API...")

    # Initialize database
    if settings.DATABASE_URL:
        await init_db()
        logger.info("Database initialized")

    # Initialize Firebase Admin SDK (if configured)
    if settings.FIREBASE_PROJECT_ID and settings.FIREBASE_PRIVATE_KEY:
        try:
            import firebase_admin
            from firebase_admin import credentials

            cred_dict = {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key": settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase: {e}")

    # Initialize MCP Proxy Server
    try:
        mcp_proxy = await get_mcp_proxy()
        logger.info("MCP Proxy Server initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize MCP proxy: {e}")

    # Start VM scheduler for auto-shutdown
    if settings.FLY_API_TOKEN:
        try:
            await start_vm_scheduler()
            logger.info("VM scheduler started")
        except Exception as e:
            logger.warning(f"Failed to start VM scheduler: {e}")
    else:
        logger.info("VM scheduler disabled (FLY_API_TOKEN not set)")

    yield

    # Shutdown
    logger.info("Shutting down Paraclete API...")

    # Stop VM scheduler
    try:
        await stop_vm_scheduler()
        logger.info("VM scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping VM scheduler: {e}")

    # Shutdown MCP proxy
    try:
        mcp_proxy = await get_mcp_proxy()
        await mcp_proxy.shutdown()
        logger.info("MCP Proxy Server shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down MCP proxy: {e}")

    await close_db()
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Mobile-first AI coding platform API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Global exception handler
@app.exception_handler(ParacleteException)
async def paraclete_exception_handler(request: Request, exc: ParacleteException):
    """Handle custom Paraclete exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    # Don't expose internal errors in production
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred"},
        )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Mobile-first AI coding platform",
        "docs": "/docs" if settings.DEBUG else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )