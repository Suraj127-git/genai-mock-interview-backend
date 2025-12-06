"""
Rate limiting middleware for API protection.
"""
from typing import Optional, Dict
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter.
    For production, use Redis-based rate limiting.
    """

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        self.last_cleanup = datetime.utcnow()

    def _cleanup_old_requests(self):
        """Remove old request timestamps to prevent memory bloat."""
        now = datetime.utcnow()

        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return

        cutoff = now - timedelta(minutes=5)

        for key in list(self.requests.keys()):
            self.requests[key] = [
                ts for ts in self.requests[key] if ts > cutoff
            ]

            if not self.requests[key]:
                del self.requests[key]

        self.last_cleanup = now

    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if request should be rate limited.

        Args:
            key: Unique identifier (e.g., user ID or IP)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if rate limited, False otherwise
        """
        self._cleanup_old_requests()

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        if key not in self.requests:
            self.requests[key] = []

        # Filter requests within window
        self.requests[key] = [
            ts for ts in self.requests[key] if ts > window_start
        ]

        # Check if limit exceeded
        if len(self.requests[key]) >= max_requests:
            return True

        # Add current request
        self.requests[key].append(now)
        return False


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

        # Different limits for different endpoints
        self.endpoint_limits = {
            "/ai-interview/sessions": (10, 60),  # 10 per minute
            "/ai-interview/sessions/{id}/message": (30, 60),  # 30 per minute
            "/ai/chat": (20, 60),  # 20 per minute
            "/auth/login": (5, 60),  # 5 per minute
            "/auth/register": (3, 60),  # 3 per minute
        }

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for client (user ID or IP)."""
        # Try to get user from auth token
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer "):
            # Would decode JWT to get user ID in production
            # For simplicity, using the token itself
            return f"user:{auth_header[7:30]}"

        # Fallback to IP address
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _get_rate_limit_for_path(self, path: str) -> tuple:
        """Get rate limit config for path."""
        # Check exact matches first
        for endpoint, limit in self.endpoint_limits.items():
            if path.startswith(endpoint.split("{")[0]):
                return limit

        # Default limit
        return (self.requests_per_minute, 60)

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Get rate limit for this endpoint
        max_requests, window_seconds = self._get_rate_limit_for_path(request.url.path)

        # Check rate limit
        rate_limit_key = f"{client_id}:{request.url.path}"

        is_limited = await rate_limiter.is_rate_limited(
            key=rate_limit_key,
            max_requests=max_requests,
            window_seconds=window_seconds
        )

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": window_seconds
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Window": str(window_seconds)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Window"] = str(window_seconds)

        return response


def setup_rate_limiting(app):
    """
    Setup rate limiting middleware.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    logger.info("Rate limiting middleware configured")
