"""
Logging configuration for the application.
"""
import logging
import sys
import time
import traceback
from typing import Any, Optional, Dict, Any as AnyType
from contextlib import contextmanager

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def capture_exception(error: Exception, **kwargs) -> None:
    """
    Capture an exception using core logging (Sentry-compatible).
    
    Args:
        error: Exception to capture
        **kwargs: Additional context (tags, extra, user, level)
    """
    logger = get_logger("error_tracking")
    
    # Extract additional context
    tags = kwargs.get('tags', {})
    extra = kwargs.get('extra', {})
    user = kwargs.get('user')
    level = kwargs.get('level', 'error')
    
    # Build log context
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "tags": tags,
        "extra": extra,
    }
    
    if user:
        context["user"] = user
    
    # Log with appropriate level
    log_level = getattr(logging, level.upper(), logging.ERROR)
    logger.log(log_level, f"Exception captured: {error}", extra=context)


def capture_message(message: str, level: str = "info", **kwargs) -> None:
    """
    Capture a message using core logging (Sentry-compatible).
    
    Args:
        message: Message to capture
        level: Severity level
        **kwargs: Additional context
    """
    logger = get_logger("message_tracking")
    
    # Extract additional context
    tags = kwargs.get('tags', {})
    extra = kwargs.get('extra', {})
    
    # Build log context
    context = {
        "message": message,
        "tags": tags,
        "extra": extra,
    }
    
    # Log with appropriate level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, f"Message captured: {message}", extra=context)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: Optional[Dict[str, Any]] = None) -> None:
    """
    Add a breadcrumb for debugging (Sentry-compatible).
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Severity level
        data: Additional data
    """
    logger = get_logger("breadcrumb")
    
    breadcrumb = {
        "message": message,
        "category": category,
        "level": level,
        "data": data or {},
        "timestamp": time.time(),
    }
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, f"Breadcrumb: {message}", extra=breadcrumb)


def set_user_context(user_id: Any, email: Optional[str] = None, **kwargs) -> None:
    """
    Set user context for logging (Sentry-compatible).
    
    Args:
        user_id: User ID (can be string or int)
        email: User email (optional)
        **kwargs: Additional user data
    """
    logger = get_logger("user_context")
    
    # Build user context
    user_context = {
        "user_id": user_id,
        **kwargs
    }
    
    if email:
        user_context["email"] = email
    
    logger.info("User context set", extra={"user": user_context})


def set_context(key: str, data: Dict[str, Any]) -> None:
    """
    Set additional context for logging (Sentry-compatible).
    
    Args:
        key: Context key
        data: Context data
    """
    logger = get_logger("context")
    logger.info(f"Context set: {key}", extra={"context_key": key, "context_data": data})


@contextmanager
def start_span(operation: str, description: Optional[str] = None):
    """
    Context manager for tracking spans/operations (Sentry-compatible).
    
    Args:
        operation: Operation name
        description: Optional description
    
    Usage:
        with start_span("database_query", "User lookup"):
            # your code here
            pass
    """
    logger = get_logger("performance")
    start_time = time.time()
    
    span_info = {
        "operation": operation,
        "description": description or operation,
        "start_time": start_time,
    }
    
    logger.debug(f"Starting span: {operation}", extra=span_info)
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        span_info["duration_seconds"] = duration
        span_info["duration_ms"] = duration * 1000
        
        logger.info(f"Completed span: {operation} in {duration:.3f}s", extra=span_info)
