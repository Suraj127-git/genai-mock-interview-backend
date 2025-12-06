"""
Main FastAPI application module.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.sentry import init_sentry
from app.middleware.cors import setup_cors
from app.middleware.error_handler import setup_error_handlers
from app.middleware.sentry_middleware import setup_sentry_middleware
from app.middleware.rate_limiter import setup_rate_limiting
from app.middleware.logging_middleware import setup_logging_middleware
from app.api.endpoints import auth, upload, sessions, ai, websocket, debug, ai_interview

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize Sentry
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize LangSmith tracing
    if settings.LANGSMITH_TRACING:
        import os
        os.environ["LANGSMITH_TRACING"] = "true"
        if settings.LANGSMITH_ENDPOINT:
            os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        logger.info(f"LangSmith tracing enabled for project: {settings.LANGSMITH_PROJECT}")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mock interview coach backend API",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Setup middleware (order matters - last added executes first)
setup_cors(app)
setup_logging_middleware(app)  # Logging first to capture all requests
setup_rate_limiting(app)  # Rate limiting before processing
setup_sentry_middleware(app)  # Sentry monitoring
setup_error_handlers(app)  # Error handling last


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    import subprocess
    try:
        git_commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd='/app').decode('utf-8').strip()
    except:
        git_commit = "unknown"

    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "git_commit": git_commit,
        "password_truncation_fix": "enabled",  # Added in commit 54b4832
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(ai_interview.router, prefix="/ai-interview", tags=["AI Interview"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

# Debug endpoints (only for testing Sentry)
if settings.DEBUG or settings.ENVIRONMENT == "development":
    app.include_router(debug.router, prefix="/debug", tags=["Debug"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
