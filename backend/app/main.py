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

    yield

    # Shutdown
    logger.info("Shutting down Paraclete API...")
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