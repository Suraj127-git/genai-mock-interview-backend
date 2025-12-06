"""
Comprehensive logging middleware for request/response tracking.
Logs all API requests with timing, user context, and structured data.
"""
import time
import json
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.core.logging import get_logger
from app.core.sentry import add_breadcrumb, set_context, start_span
from app.core.monitoring import log_metric, log_user_action

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses with comprehensive data.
    """

    def __init__(self, app):
        super().__init__(app)
        self.excluded_paths = ["/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log comprehensive information.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response
        """
        # Generate request ID for tracking
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Extract request information
        start_time = time.time()
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"

        # Extract user info from headers (if authenticated)
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Would decode JWT to get user_id in production
            # For now, we'll set it in the endpoint if available
            pass

        # Build request log data
        request_log_data = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "query_params": query_params,
            "client_host": client_host,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }

        # Log request start
        logger.info(
            f"→ {method} {path}",
            extra={
                **request_log_data,
                "event": "request_start",
                "timestamp": start_time
            }
        )

        add_breadcrumb(
            f"Request: {method} {path}",
            category="http",
            level="info",
            data=request_log_data
        )

        # Set Sentry context
        set_context("request", request_log_data)

        # Log request body for non-GET requests (excluding sensitive data)
        if method in ["POST", "PUT", "PATCH"]:
            try:
                if request.headers.get("content-type") == "application/json":
                    body = await request.body()
                    if body:
                        try:
                            body_json = json.loads(body.decode())
                            # Remove sensitive fields
                            safe_body = self._sanitize_body(body_json)
                            request_log_data["body_preview"] = str(safe_body)[:500]
                        except:
                            request_log_data["body_preview"] = "Could not parse JSON"

                        # Important: Reset request body for downstream processing
                        async def receive():
                            return {"type": "http.request", "body": body}
                        request._receive = receive
            except Exception as e:
                logger.debug(f"Could not read request body: {e}")

        # Process request with span tracking
        response = None
        status_code = 500  # Default in case of error
        error_occurred = False
        error_details = None

        try:
            with start_span("http.request", f"{method} {path}"):
                response = await call_next(request)
                status_code = response.status_code

        except Exception as e:
            error_occurred = True
            error_details = {
                "error_type": e.__class__.__name__,
                "error_message": str(e)
            }
            logger.error(
                f"Error processing request: {method} {path}",
                exc_info=True,
                extra={
                    **request_log_data,
                    **error_details,
                    "event": "request_error"
                }
            )
            raise

        finally:
            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # Build response log data
            response_log_data = {
                **request_log_data,
                "status_code": status_code,
                "duration_seconds": duration,
                "duration_ms": duration_ms,
                "event": "request_complete"
            }

            if error_occurred and error_details:
                response_log_data.update(error_details)

            # Determine log level based on status code
            if status_code >= 500:
                log_level = "error"
            elif status_code >= 400:
                log_level = "warning"
            else:
                log_level = "info"

            # Log response
            getattr(logger, log_level)(
                f"← {method} {path} {status_code} ({duration_ms:.2f}ms)",
                extra=response_log_data
            )

            # Add response headers
            if response:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log metrics
            log_metric(f"http_request_{method.lower()}", 1, {
                "path": path,
                "status_code": str(status_code),
                "status_category": f"{status_code // 100}xx"
            })

            log_metric("http_request_duration_ms", duration_ms, {
                "method": method,
                "path": path,
                "status_code": str(status_code)
            })

            # Add breadcrumb for response
            add_breadcrumb(
                f"Response: {method} {path} {status_code}",
                category="http",
                level=log_level,
                data={
                    "status_code": status_code,
                    "duration_ms": duration_ms
                }
            )

            # Log slow requests
            if duration_ms > 1000:  # > 1 second
                logger.warning(
                    f"Slow request detected: {method} {path} took {duration_ms:.2f}ms",
                    extra={
                        **response_log_data,
                        "event": "slow_request",
                        "threshold_ms": 1000
                    }
                )

                log_metric("http_slow_request", 1, {
                    "method": method,
                    "path": path,
                    "duration_ms": str(int(duration_ms))
                })

        return response

    def _sanitize_body(self, body: dict) -> dict:
        """
        Remove sensitive fields from request body for logging.

        Args:
            body: Request body as dict

        Returns:
            Sanitized body dict
        """
        sensitive_fields = [
            'password',
            'token',
            'secret',
            'api_key',
            'access_token',
            'refresh_token',
            'hashed_password',
            'credit_card',
            'ssn'
        ]

        def sanitize_recursive(obj):
            if isinstance(obj, dict):
                return {
                    k: '***REDACTED***' if any(sens in k.lower() for sens in sensitive_fields)
                    else sanitize_recursive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [sanitize_recursive(item) for item in obj]
            else:
                return obj

        return sanitize_recursive(body)


class ResponseLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log response bodies for debugging.
    Only enabled in development mode.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process response and optionally log body."""
        response = await call_next(request)

        # Only log response bodies in development and for certain paths
        if request.app.debug and request.url.path.startswith("/api"):
            # Don't log streaming responses
            if not isinstance(response, StreamingResponse):
                try:
                    # Read response body
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk

                    # Try to parse as JSON
                    try:
                        response_json = json.loads(body.decode())
                        logger.debug(
                            f"Response body for {request.method} {request.url.path}",
                            extra={
                                "request_id": getattr(request.state, "request_id", "unknown"),
                                "response_preview": str(response_json)[:500]
                            }
                        )
                    except:
                        logger.debug(
                            f"Non-JSON response for {request.method} {request.url.path}",
                            extra={
                                "request_id": getattr(request.state, "request_id", "unknown"),
                                "content_type": response.headers.get("content-type")
                            }
                        )

                    # Recreate response with body
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )

                except Exception as e:
                    logger.debug(f"Could not log response body: {e}")

        return response


class UserActionLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log user actions for analytics.
    """

    def __init__(self, app):
        super().__init__(app)
        self.action_paths = {
            "/auth/register": "user_registered",
            "/auth/login": "user_login",
            "/auth/logout": "user_logout",
            "/ai-interview/sessions": "interview_started",
            "/ai-interview/profile": "profile_updated",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log user actions based on path and method."""
        response = await call_next(request)

        # Check if this is an action we want to log
        path = request.url.path
        method = request.method

        for action_path, action_name in self.action_paths.items():
            if path.startswith(action_path):
                # Extract user_id if available (would be from JWT or session)
                user_id = getattr(request.state, "user_id", None)

                if user_id:
                    log_user_action(
                        user_id=user_id,
                        action=action_name,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "request_id": getattr(request.state, "request_id", "unknown")
                        }
                    )

        return response


def setup_logging_middleware(app):
    """
    Setup all logging middleware.

    Args:
        app: FastAPI application instance
    """
    # Add in reverse order (last added executes first)
    app.add_middleware(UserActionLoggingMiddleware)
    app.add_middleware(ResponseLoggingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Logging middleware configured successfully")
