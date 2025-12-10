"""
Sentry integration for error tracking and performance monitoring.
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.

    Features enabled:
    - Error tracking with stack traces
    - Performance monitoring (transactions)
    - Breadcrumbs for debugging
    - User context
    - Request data
    - SQL query tracking
    """
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured. Sentry monitoring disabled.")
        return

    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            # Performance Monitoring
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            # Enable performance monitoring for database queries
            enable_tracing=True,
            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",  # Use endpoint name for transaction names
                    failed_request_status_codes=[403, range(500, 599)],
                ),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR,  # Send errors as events
                ),
            ],
            # Send default PII (Personally Identifiable Information)
            send_default_pii=True,
            # Attach stack traces to messages
            attach_stacktrace=True,
            # Include local variables in stack traces
            include_local_variables=True,
            # Max breadcrumbs
            max_breadcrumbs=50,
            # Release tracking (use git commit hash in production)
            release=f"genai-coach-backend@{settings.APP_VERSION}",
            # Sample rate for error events (1.0 = 100%)
            sample_rate=1.0,
            # Before send hook to modify events
            before_send=before_send_filter,
            # Before breadcrumb hook
            before_breadcrumb=before_breadcrumb_filter,
        )

        logger.info(
            f"Sentry initialized successfully. Environment: {settings.SENTRY_ENVIRONMENT}, "
            f"Traces Sample Rate: {settings.SENTRY_TRACES_SAMPLE_RATE}"
        )

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event, hint):
    """
    Filter and modify events before sending to Sentry.

    Use this to:
    - Remove sensitive data
    - Filter out certain errors
    - Add custom tags
    """
    # Skip certain exceptions
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Don't send 404 errors to Sentry
        if exc_type.__name__ == "HTTPException":
            if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
                return None

        # Don't send validation errors (422) to Sentry
        if exc_type.__name__ == "RequestValidationError":
            return None

    # Remove sensitive data from request body
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            # Remove password fields
            for key in ["password", "current_password", "new_password"]:
                if key in data:
                    data[key] = "[FILTERED]"
            # Remove tokens
            for key in ["token", "refresh_token", "access_token"]:
                if key in data:
                    data[key] = "[FILTERED]"

    # Add custom tags
    event["tags"] = event.get("tags", {})
    event["tags"]["environment"] = settings.ENVIRONMENT
    event["tags"]["app_version"] = settings.APP_VERSION

    return event


def before_breadcrumb_filter(crumb, hint):
    """
    Filter and modify breadcrumbs before adding to event.

    Use this to:
    - Remove sensitive data from breadcrumbs
    - Filter out noisy breadcrumbs
    """
    # Remove sensitive data from query breadcrumbs
    if crumb.get("category") == "query":
        message = crumb.get("message", "")
        if "password" in message.lower():
            crumb["message"] = "[FILTERED SQL QUERY]"

    return crumb


def capture_exception(error: Exception, **kwargs) -> None:
    """
    Manually capture an exception and send to Sentry.

    Args:
        error: Exception to capture
        **kwargs: Additional context (tags, extra data, user info)

    Example:
        capture_exception(
            error,
            tags={"service": "ai_service"},
            extra={"model": "gpt-4"},
            user={"id": user.id, "email": user.email}
        )
    """
    if not settings.SENTRY_DSN:
        return

    with sentry_sdk.push_scope() as scope:
        # Add tags
        if "tags" in kwargs:
            for key, value in kwargs["tags"].items():
                scope.set_tag(key, value)

        # Add extra context
        if "extra" in kwargs:
            for key, value in kwargs["extra"].items():
                scope.set_extra(key, value)

        # Add user context
        if "user" in kwargs:
            scope.set_user(kwargs["user"])

        # Set level
        if "level" in kwargs:
            scope.level = kwargs["level"]

        sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", **kwargs) -> None:
    """
    Manually capture a message and send to Sentry.

    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context (tags, extra data)

    Example:
        capture_message(
            "User login failed",
            level="warning",
            tags={"auth_type": "email"},
            extra={"email": user_email}
        )
    """
    if not settings.SENTRY_DSN:
        return

    with sentry_sdk.push_scope() as scope:
        # Add tags
        if "tags" in kwargs:
            for key, value in kwargs["tags"].items():
                scope.set_tag(key, value)

        # Add extra context
        if "extra" in kwargs:
            for key, value in kwargs["extra"].items():
                scope.set_extra(key, value)

        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str = None, **kwargs) -> None:
    """
    Set user context for all subsequent Sentry events.

    Args:
        user_id: User ID
        email: User email
        **kwargs: Additional user data
    """
    if not settings.SENTRY_DSN:
        return

    user_data = {"id": user_id}
    if email:
        user_data["email"] = email
    user_data.update(kwargs)

    sentry_sdk.set_user(user_data)


def set_context(key: str, data: dict) -> None:
    """
    Set custom context for all subsequent Sentry events.

    Args:
        key: Context key (e.g., "database", "api_request")
        data: Context data dictionary

    Example:
        set_context("api_call", {
            "endpoint": "/ai/chat",
            "model": "gpt-4",
            "tokens": 150
        })
    """
    if not settings.SENTRY_DSN:
        return

    sentry_sdk.set_context(key, data)


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **kwargs) -> None:
    """
    Add a breadcrumb for debugging context.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "database", "api")
        level: Severity level
        **kwargs: Additional breadcrumb data

    Example:
        add_breadcrumb(
            "User attempted login",
            category="auth",
            level="info",
            data={"email": user_email, "ip": request_ip}
        )
    """
    if not settings.SENTRY_DSN:
        return

    breadcrumb = {
        "message": message,
        "category": category,
        "level": level,
    }

    if "data" in kwargs:
        breadcrumb["data"] = kwargs["data"]

    sentry_sdk.add_breadcrumb(breadcrumb)


def start_transaction(name: str, op: str = "function") -> sentry_sdk.tracing.Transaction:
    """
    Start a performance monitoring transaction.

    Args:
        name: Transaction name
        op: Operation type (e.g., "http.server", "db.query", "function")

    Returns:
        Transaction object (use as context manager)

    Example:
        with start_transaction("generate_feedback", op="ai.inference"):
            result = await ai_service.generate_feedback(...)
    """
    if not settings.SENTRY_DSN:
        # Return a no-op context manager
        class NoOpTransaction:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return NoOpTransaction()

    return sentry_sdk.start_transaction(name=name, op=op)


def start_span(operation: str, description: str = None) -> sentry_sdk.tracing.Span:
    """
    Start a span within the current transaction.

    Args:
        operation: Span operation (e.g., "db.query", "http.request")
        description: Span description

    Returns:
        Span object (use as context manager)

    Example:
        with start_span("db.query", "Fetch user sessions"):
            sessions = await session_service.get_user_sessions(...)
    """
    if not settings.SENTRY_DSN:
        # Return a no-op context manager
        class NoOpSpan:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return NoOpSpan()

    return sentry_sdk.start_span(op=operation, description=description)
