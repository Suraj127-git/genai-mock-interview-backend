"""
Sentry middleware for enhanced request tracking and user context.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from app.core.sentry import set_user_context, set_context, add_breadcrumb
from app.core.config import settings


class SentryContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add context to Sentry events.

    This middleware:
    - Sets user context from JWT token
    - Adds request context (method, URL, headers)
    - Adds breadcrumbs for request lifecycle
    - Tracks request duration
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add Sentry context."""
        if not settings.SENTRY_DSN:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Extract user from request state (set by auth dependency)
        user = getattr(request.state, "user", None)
        if user:
            set_user_context(
                user_id=str(user.id),
                email=user.email,
                name=user.name,
            )

        # Add request context
        set_context("request", {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        })

        # Add breadcrumb for request start
        add_breadcrumb(
            f"{request.method} {request.url.path}",
            category="http.request",
            level="info",
            data={
                "method": request.method,
                "url": str(request.url),
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Add breadcrumb for successful response
            add_breadcrumb(
                f"Response {response.status_code}",
                category="http.response",
                level="info" if response.status_code < 400 else "warning",
                data={
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Add breadcrumb for error
            add_breadcrumb(
                f"Request failed: {str(e)}",
                category="http.error",
                level="error",
                data={
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                }
            )

            # Re-raise to let error handler deal with it
            raise


def setup_sentry_middleware(app):
    """
    Setup Sentry middleware on FastAPI app.

    Args:
        app: FastAPI application instance
    """
    if settings.SENTRY_DSN:
        app.add_middleware(SentryContextMiddleware)
