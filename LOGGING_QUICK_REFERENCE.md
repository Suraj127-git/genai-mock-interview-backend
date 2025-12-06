# Logging & Monitoring - Quick Reference

## Import Statements

```python
# Core logging
from app.core.logging import get_logger

# Sentry integration
from app.core.sentry import (
    start_span,
    capture_exception,
    add_breadcrumb,
    set_context
)

# Monitoring utilities
from app.core.monitoring import (
    track_time,
    log_step,
    log_metric,
    log_function_call,
    log_user_action,
    log_error,
    log_warning
)
```

## Common Patterns

### Basic Logging
```python
logger = get_logger(__name__)

# Simple log
logger.info("Operation started")

# With context
logger.info("Processing user", extra={
    "user_id": 123,
    "operation": "create_profile"
})

# Error with stack trace
logger.error("Failed to process", exc_info=True, extra={
    "user_id": 123
})
```

### Performance Tracking
```python
# Time an operation
with track_time("operation_name", {"user_id": 123}):
    result = await expensive_operation()
# Logs: "Completed operation_name in 1.234s"

# Time a code block
with start_span("database.query", "Fetch users"):
    users = await db.execute(query)
```

### Function Logging
```python
# Automatic logging of calls, timing, errors
@log_function_call(level="info", log_args=True, log_result=True)
async def process_data(user_id: int, session_id: int):
    return result
```

### Workflow Steps
```python
log_step("Step 1: Fetch Data", {"user_id": 123})
# ... do work ...
log_step("Step 2: Process", {"records_found": 50})
# ... do work ...
log_step("Complete", {"status": "success"})
```

### Error Handling
```python
try:
    result = await risky_operation()
except Exception as e:
    log_error(
        error=e,
        operation="risky_operation",
        user_id=123,
        extra_data={"attempt": 3}
    )
```

### Metrics
```python
# Count metric
log_metric("users_created", 1, {"source": "api"})

# Value metric
log_metric("response_time_ms", 234.56, {"endpoint": "/api/users"})

# Gauge metric
log_metric("active_sessions", 42)
```

### User Actions
```python
log_user_action(
    user_id=123,
    action="interview_completed",
    details={
        "session_id": 456,
        "score": 85.5,
        "duration_seconds": 1800
    }
)
```

### Breadcrumbs
```python
# Add debugging breadcrumbs
add_breadcrumb(
    "Database Query",
    category="database",
    level="info",
    data={"query": "SELECT users", "count": 50}
)

add_breadcrumb(
    "LLM Call",
    category="ai",
    level="info",
    data={"model": "llama-3.3-70b", "tokens": 500}
)
```

### Context Setting
```python
# Set context for error reports
set_context("user", {
    "user_id": 123,
    "email": "user@example.com",
    "subscription": "premium"
})

set_context("request", {
    "request_id": "abc-123",
    "path": "/api/interviews",
    "method": "POST"
})
```

## HTTP Request Logging

### Automatic
All requests automatically logged with:
- Request ID
- Method and path
- Duration
- Status code
- Client IP

### Headers Added to Response
```
X-Request-ID: abc-123-def
X-Response-Time: 234.56ms
```

### Finding Request Logs
```bash
grep "request_id\":\"abc-123-def" logs/app.log
```

## Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| DEBUG | Development details | `logger.debug("Parsing JSON", extra={...})` |
| INFO | Normal operations | `logger.info("User logged in", extra={...})` |
| WARNING | Recoverable issues | `logger.warning("Cache miss", extra={...})` |
| ERROR | Errors requiring attention | `logger.error("DB connection failed", exc_info=True)` |
| CRITICAL | System failures | `logger.critical("Service down")` |

## Sentry Quick Commands

```python
# Capture exception
capture_exception(e, tags={"operation": "user_create"})

# Add breadcrumb
add_breadcrumb("Step 1", category="workflow", data={...})

# Set context
set_context("user", {"user_id": 123})

# Track span
with start_span("operation", "Description"):
    do_work()
```

## Environment Variables

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=1.0  # 0.0 to 1.0

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxx
LANGCHAIN_PROJECT=genai-mock-interview
```

## Common Log Searches

```bash
# All errors
grep '"level":"ERROR"' logs/app.log

# Specific user
grep '"user_id":123' logs/app.log

# Specific request
grep '"request_id":"abc-123"' logs/app.log

# Slow requests
grep '"slow_request"' logs/app.log

# User actions
grep '"action_category":"user_interaction"' logs/app.log

# Last 100 requests
tail -n 100 logs/app.log | grep '"event":"request_complete"'
```

## Monitoring Checklist

Daily:
- [ ] Check error rate in Sentry
- [ ] Review slow requests (> 1s)
- [ ] Monitor LLM token usage
- [ ] Check success rate of key endpoints

Weekly:
- [ ] Review performance trends
- [ ] Analyze user behavior patterns
- [ ] Check log file sizes
- [ ] Update alert thresholds

## Debugging Workflow

1. **Find Error**: Check Sentry or logs
2. **Get Request ID**: From error message
3. **View Full Context**: `grep request_id logs/app.log`
4. **Check Breadcrumbs**: In Sentry
5. **View Trace**: In LangSmith (for AI operations)
6. **Identify Root Cause**: From logs + traces
7. **Fix & Deploy**: Monitor metrics

## Complete Example

```python
from app.core.logging import get_logger
from app.core.monitoring import track_time, log_step, log_metric, log_error
from app.core.sentry import add_breadcrumb, set_context

logger = get_logger(__name__)

async def process_interview(user_id: int, session_id: int):
    """Complete example with all logging best practices."""

    # Set context
    set_context("interview", {
        "user_id": user_id,
        "session_id": session_id
    })

    logger.info("Processing interview", extra={
        "user_id": user_id,
        "session_id": session_id
    })

    try:
        # Step 1
        log_step("Fetch Session", {"session_id": session_id})
        add_breadcrumb("Fetch session", category="database")

        with track_time("fetch_session"):
            session = await get_session(session_id)

        # Step 2
        log_step("Generate Assessment", {
            "interaction_count": len(session.interactions)
        })

        with track_time("generate_assessment"):
            assessment = await generate_assessment(session)

        # Log metrics
        log_metric("assessment_generated", 1)
        log_metric("overall_score", assessment.score)

        # Success
        log_step("Complete", {"status": "success", "score": assessment.score})

        logger.info("Interview processed successfully", extra={
            "user_id": user_id,
            "session_id": session_id,
            "score": assessment.score
        })

        return assessment

    except Exception as e:
        log_error(e, "process_interview", user_id=user_id, extra_data={
            "session_id": session_id
        })
        raise
```

## Performance Tips

- Use DEBUG level only in development
- Sample Sentry traces in production (10-20%)
- Don't log request/response bodies in production
- Rotate logs to prevent disk fill
- Use async logging for high throughput

## Resources

- **Full Documentation**: [LOGGING_MONITORING.md](LOGGING_MONITORING.md)
- **Implementation Summary**: [LOGGING_IMPLEMENTATION_SUMMARY.md](LOGGING_IMPLEMENTATION_SUMMARY.md)
- **Sentry Dashboard**: https://sentry.io
- **LangSmith Dashboard**: https://smith.langchain.com

---

**Quick Start**: Just add `@log_function_call()` decorator and you're 80% there!
