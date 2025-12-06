"""
Comprehensive monitoring, logging, and metrics utilities.
Integrates with Sentry for error tracking and performance monitoring.
"""
import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

from app.core.logging import get_logger
from app.core.sentry import (
    start_span,
    capture_exception,
    add_breadcrumb,
    set_context,
    capture_message
)

logger = get_logger(__name__)


class PerformanceMonitor:
    """Monitor and log performance metrics."""

    @staticmethod
    @contextmanager
    def track_time(operation_name: str, extra_data: Optional[Dict[str, Any]] = None):
        """
        Context manager to track execution time of operations.

        Usage:
            with PerformanceMonitor.track_time("database_query", {"query": "SELECT"}):
                # your code here
                pass
        """
        start_time = time.time()
        extra_data = extra_data or {}

        logger.debug(f"Starting {operation_name}", extra={
            "operation": operation_name,
            **extra_data
        })

        add_breadcrumb(
            f"Start: {operation_name}",
            category="performance",
            level="info",
            data=extra_data
        )

        try:
            with start_span(f"perf.{operation_name}", operation_name):
                yield
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error in {operation_name} after {duration:.3f}s",
                exc_info=True,
                extra={
                    "operation": operation_name,
                    "duration_seconds": duration,
                    "error": str(e),
                    **extra_data
                }
            )
            capture_exception(
                e,
                tags={
                    "operation": operation_name,
                    "performance": "tracked"
                },
                extra={
                    "duration_seconds": duration,
                    **extra_data
                }
            )
            raise
        finally:
            duration = time.time() - start_time
            logger.info(
                f"Completed {operation_name} in {duration:.3f}s",
                extra={
                    "operation": operation_name,
                    "duration_seconds": duration,
                    "duration_ms": duration * 1000,
                    **extra_data
                }
            )

            add_breadcrumb(
                f"Complete: {operation_name}",
                category="performance",
                level="info",
                data={
                    "duration_seconds": duration,
                    **extra_data
                }
            )


def log_function_call(
    level: str = "info",
    log_args: bool = True,
    log_result: bool = False,
    track_performance: bool = True
):
    """
    Decorator to log function calls with arguments and results.

    Args:
        level: Log level (debug, info, warning, error)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        track_performance: Whether to track execution time

    Usage:
        @log_function_call(level="debug", log_args=True, log_result=True)
        async def my_function(arg1, arg2):
            return result
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            # Prepare log data
            log_data = {
                "function": func_name,
                "is_async": True
            }

            if log_args:
                # Don't log sensitive data
                safe_args = []
                for arg in args:
                    if hasattr(arg, '__class__'):
                        safe_args.append(f"<{arg.__class__.__name__}>")
                    else:
                        safe_args.append(str(arg)[:100])  # Limit length

                safe_kwargs = {
                    k: (v if k not in ['password', 'token', 'secret', 'key'] else '***')
                    for k, v in kwargs.items()
                }

                log_data.update({
                    "args": safe_args,
                    "kwargs": safe_kwargs
                })

            # Log function call
            getattr(logger, level)(f"Calling {func_name}", extra=log_data)

            add_breadcrumb(
                f"Call: {func_name}",
                category="function_call",
                level=level,
                data=log_data
            )

            start_time = time.time()

            try:
                # Execute function
                if track_performance:
                    with start_span(f"func.{func_name}", func_name):
                        result = await func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

                duration = time.time() - start_time

                # Log completion
                completion_data = {
                    **log_data,
                    "duration_seconds": duration,
                    "duration_ms": duration * 1000,
                    "status": "success"
                }

                if log_result:
                    result_str = str(result)[:200]  # Limit length
                    completion_data["result"] = result_str

                getattr(logger, level)(
                    f"Completed {func_name} in {duration:.3f}s",
                    extra=completion_data
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"Error in {func_name} after {duration:.3f}s: {str(e)}",
                    exc_info=True,
                    extra={
                        **log_data,
                        "duration_seconds": duration,
                        "error": str(e),
                        "error_type": e.__class__.__name__,
                        "status": "error"
                    }
                )

                capture_exception(
                    e,
                    tags={
                        "function": func_name,
                        "is_async": "true"
                    },
                    extra=log_data
                )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            log_data = {
                "function": func_name,
                "is_async": False
            }

            if log_args:
                safe_args = [str(arg)[:100] for arg in args]
                safe_kwargs = {
                    k: (v if k not in ['password', 'token', 'secret', 'key'] else '***')
                    for k, v in kwargs.items()
                }
                log_data.update({
                    "args": safe_args,
                    "kwargs": safe_kwargs
                })

            getattr(logger, level)(f"Calling {func_name}", extra=log_data)

            start_time = time.time()

            try:
                if track_performance:
                    with start_span(f"func.{func_name}", func_name):
                        result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                duration = time.time() - start_time

                completion_data = {
                    **log_data,
                    "duration_seconds": duration,
                    "status": "success"
                }

                if log_result:
                    completion_data["result"] = str(result)[:200]

                getattr(logger, level)(
                    f"Completed {func_name} in {duration:.3f}s",
                    extra=completion_data
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"Error in {func_name} after {duration:.3f}s: {str(e)}",
                    exc_info=True,
                    extra={
                        **log_data,
                        "duration_seconds": duration,
                        "error": str(e),
                        "error_type": e.__class__.__name__,
                        "status": "error"
                    }
                )

                capture_exception(e, tags={"function": func_name}, extra=log_data)
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class DataLogger:
    """Helper for logging structured data at different stages."""

    @staticmethod
    def log_step(
        step_name: str,
        data: Dict[str, Any],
        level: str = "info",
        category: str = "workflow"
    ):
        """
        Log a workflow step with structured data.

        Args:
            step_name: Name of the step
            data: Structured data to log
            level: Log level
            category: Category for breadcrumb
        """
        log_data = {
            "step": step_name,
            "category": category,
            **data
        }

        getattr(logger, level)(f"Step: {step_name}", extra=log_data)

        add_breadcrumb(
            step_name,
            category=category,
            level=level,
            data=data
        )

    @staticmethod
    def log_metric(metric_name: str, value: Any, tags: Optional[Dict[str, str]] = None):
        """
        Log a metric value.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for categorization
        """
        tags = tags or {}

        logger.info(f"Metric: {metric_name}", extra={
            "metric_name": metric_name,
            "metric_value": value,
            "metric_type": type(value).__name__,
            **tags
        })

        set_context(f"metric_{metric_name}", {
            "value": value,
            **tags
        })

    @staticmethod
    def log_user_action(
        user_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a user action for analytics.

        Args:
            user_id: User ID
            action: Action name
            details: Additional details
        """
        details = details or {}

        logger.info(f"User action: {action}", extra={
            "user_id": user_id,
            "action": action,
            "action_category": "user_interaction",
            **details
        })

        add_breadcrumb(
            f"User Action: {action}",
            category="user",
            level="info",
            data={
                "user_id": user_id,
                **details
            }
        )

        set_context("user_context", {
            "user_id": user_id,
            "last_action": action
        })


class ErrorLogger:
    """Centralized error logging with context."""

    @staticmethod
    def log_error(
        error: Exception,
        operation: str,
        user_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log an error with full context.

        Args:
            error: The exception
            operation: Operation that failed
            user_id: Optional user ID
            extra_data: Additional context data
        """
        extra_data = extra_data or {}

        log_data = {
            "operation": operation,
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            **extra_data
        }

        if user_id:
            log_data["user_id"] = user_id

        logger.error(
            f"Error in {operation}: {str(error)}",
            exc_info=True,
            extra=log_data
        )

        # Capture to Sentry
        capture_exception(
            error,
            tags={
                "operation": operation,
                "error_type": error.__class__.__name__
            },
            extra=log_data
        )

        # Add breadcrumb
        add_breadcrumb(
            f"Error: {operation}",
            category="error",
            level="error",
            data=log_data
        )

    @staticmethod
    def log_warning(
        message: str,
        operation: str,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log a warning with context.

        Args:
            message: Warning message
            operation: Operation context
            extra_data: Additional data
        """
        extra_data = extra_data or {}

        log_data = {
            "operation": operation,
            **extra_data
        }

        logger.warning(message, extra=log_data)

        add_breadcrumb(
            f"Warning: {operation}",
            category="warning",
            level="warning",
            data=log_data
        )


# Convenience exports
track_time = PerformanceMonitor.track_time
log_step = DataLogger.log_step
log_metric = DataLogger.log_metric
log_user_action = DataLogger.log_user_action
log_error = ErrorLogger.log_error
log_warning = ErrorLogger.log_warning
