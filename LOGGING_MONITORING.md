# Comprehensive Logging & Monitoring Guide

## Overview

The AI Interview backend implements comprehensive logging, monitoring, and observability across all services. Every operation is tracked with structured logs, performance metrics, and Sentry integration for debugging and analytics.

## Architecture

### Logging Layers

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (Services, Endpoints, Business Logic)  │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────┐  ┌──────▼───────┐
│   Logging    │  │   Monitoring │
│   Module     │  │    Module    │
└───────┬──────┘  └──────┬───────┘
        │                │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐  ┌────▼────┐  ┌───▼────┐
│ Files │  │  Sentry │  │LangSmith│
│ Logs  │  │  Cloud  │  │ Traces  │
└───────┘  └─────────┘  └────────┘
```

### Key Components

1. **Core Logging** (`app/core/logging.py`)
   - Structured JSON logging
   - Multiple log levels
   - File and console output

2. **Sentry Integration** (`app/core/sentry.py`)
   - Error tracking
   - Performance monitoring
   - Breadcrumbs and context

3. **Monitoring Utilities** (`app/core/monitoring.py`)
   - Performance tracking
   - Function call logging
   - Metrics collection
   - Error handling

4. **HTTP Logging Middleware** (`app/middleware/logging_middleware.py`)
   - Request/response logging
   - Timing metrics
   - User action tracking

## Log Formats

### Structured Logging

All logs are emitted in structured JSON format for easy parsing:

```json
{
  "timestamp": "2025-12-07T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.services.rag_service",
  "message": "Starting RAG indexing for user 123",
  "extra": {
    "user_id": 123,
    "operation": "index_user_context",
    "request_id": "abc-123-def"
  }
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Critical issues that may cause the application to abort

## Usage Examples

### 1. Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Processing user request")

# With extra data
logger.info("User logged in", extra={
    "user_id": 123,
    "email": "user@example.com",
    "ip_address": "192.168.1.1"
})

# Error logging
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True, extra={
        "operation": "risky_operation",
        "user_id": 123
    })
```

### 2. Performance Tracking

```python
from app.core.monitoring import track_time, log_metric

# Track execution time
with track_time("database_query", {"query": "SELECT users"}):
    results = await db.execute(query)
    # Automatically logs: "Completed database_query in 0.123s"

# Log custom metrics
log_metric("users_indexed", 150, tags={"operation": "rag_indexing"})
```

### 3. Function Call Logging

```python
from app.core.monitoring import log_function_call

@log_function_call(level="info", log_args=True, log_result=True)
async def process_interview(user_id: int, session_id: int):
    """Process interview session."""
    # Function automatically logs:
    # - Call with arguments
    # - Execution time
    # - Result
    # - Any errors
    return result
```

### 4. Step-by-Step Logging

```python
from app.core.monitoring import log_step

# Log workflow steps
log_step("Fetch User Data", {
    "user_id": 123,
    "operation": "index_user"
})

log_step("Build Documents", {
    "document_count": 15,
    "types": ["profile", "resume", "history"]
})

log_step("Index Complete", {
    "duration_ms": 1234,
    "status": "success"
})
```

### 5. Error Logging with Context

```python
from app.core.monitoring import log_error, log_warning

try:
    process_data()
except Exception as e:
    log_error(
        error=e,
        operation="process_data",
        user_id=123,
        extra_data={
            "data_size": 1000,
            "step": "validation"
        }
    )

# Warnings
log_warning(
    message="Cache miss, fetching from database",
    operation="get_user_profile",
    extra_data={"user_id": 123}
)
```

### 6. User Action Logging

```python
from app.core.monitoring import log_user_action

log_user_action(
    user_id=123,
    action="interview_completed",
    details={
        "session_id": 456,
        "duration_seconds": 1800,
        "score": 85.5
    }
)
```

## HTTP Request Logging

### Automatic Request/Response Logging

All HTTP requests are automatically logged with:

- Request ID (for tracking)
- Method and path
- Query parameters
- Client IP and user agent
- Request body (sanitized)
- Response status code
- Response time
- Slow request detection

Example log output:

```
→ POST /ai-interview/sessions
  request_id: abc-123-def
  user_id: 123
  body: {"title": "Technical Interview", "type": "technical"}

← POST /ai-interview/sessions 201 (1234.56ms)
  request_id: abc-123-def
  status: success
  duration_ms: 1234.56
```

### Request ID Tracking

Every request gets a unique ID that's:
- Added to all logs related to that request
- Included in response headers (`X-Request-ID`)
- Used for correlation across services

## Sentry Integration

### Error Tracking

Errors are automatically captured in Sentry with:
- Stack traces
- User context
- Request context
- Custom tags and extra data

```python
from app.core.sentry import capture_exception, add_breadcrumb, set_context

# Add breadcrumbs for debugging
add_breadcrumb(
    "User Profile Fetch",
    category="database",
    level="info",
    data={"user_id": 123}
)

# Set context for error reports
set_context("user_info", {
    "user_id": 123,
    "email": "user@example.com",
    "subscription": "premium"
})

# Errors are auto-captured, but you can manually capture too
try:
    risky_operation()
except Exception as e:
    capture_exception(
        e,
        tags={"operation": "risky_op", "critical": "true"},
        extra={"attempt": 3}
    )
```

### Performance Monitoring

Performance spans are tracked automatically:

```python
from app.core.sentry import start_span

with start_span("rag.index", "Index user context"):
    with start_span("rag.fetch_data", "Fetch from database"):
        user = await fetch_user()

    with start_span("rag.build_docs", "Build documents"):
        documents = build_documents(user)

    with start_span("rag.vector_store", "Add to vector store"):
        vector_store.add_documents(documents)
```

View performance waterfall in Sentry dashboard.

## LangSmith Integration

### AI Operation Tracing

All LLM calls and LangGraph workflows are traced in LangSmith:

```python
# Automatic tracing when LANGCHAIN_TRACING_V2=true
from langchain_groq import ChatGroq

llm = ChatGroq(api_key=settings.GROQ_API_KEY)
response = await llm.ainvoke(messages)  # Automatically traced

# View in LangSmith:
# - Full conversation
# - Token usage
# - Latency
# - Errors
```

Access traces at: https://smith.langchain.com

## Metrics Collection

### Types of Metrics

1. **Counter Metrics** (incremental counts)
   ```python
   log_metric("rag_documents_indexed", 15)
   log_metric("interviews_started", 1)
   ```

2. **Gauge Metrics** (current value)
   ```python
   log_metric("active_sessions", 42)
   log_metric("cache_hit_rate", 0.85)
   ```

3. **Timing Metrics** (durations)
   ```python
   log_metric("rag_index_duration_ms", 1234.56)
   log_metric("llm_response_time_ms", 876.43)
   ```

### Common Metrics Tracked

- `http_request_<method>`: HTTP requests by method
- `http_request_duration_ms`: Request processing time
- `http_slow_request`: Requests over 1 second
- `rag_documents_indexed`: Documents added to vector store
- `rag_documents_retrieved`: Documents retrieved from vector store
- `llm_tokens_used`: Token usage per call
- `assessment_generated`: Assessments completed
- `user_action_<action>`: User actions

## Log Files

### File Locations

```
logs/
├── app.log              # All logs
├── error.log            # Errors only
└── access.log           # HTTP access logs (optional)
```

### Rotation

Logs are automatically rotated:
- **Max size**: 10 MB per file
- **Backups**: 5 backup files kept
- **Compression**: Old logs compressed

## Monitoring Dashboard

### What to Monitor

1. **Error Rate**
   - Track 4xx and 5xx response rates
   - Alert on sudden spikes

2. **Response Time**
   - p50, p95, p99 latencies
   - Identify slow endpoints

3. **LLM Usage**
   - Token consumption
   - API call success rate
   - Average response time

4. **RAG Performance**
   - Indexing success rate
   - Retrieval latency
   - Document count per user

5. **User Activity**
   - New registrations
   - Interviews started/completed
   - Profile updates

### Example Queries

**Sentry**:
```
# Find slow requests
release:latest transaction.duration:>1000

# Find errors for specific user
user.id:123 level:error

# Find RAG indexing failures
transaction:"rag.index_user" status:error
```

**Log Analysis**:
```bash
# Count errors in last hour
grep '"level":"ERROR"' logs/app.log | tail -n 1000

# Find slow requests
grep '"duration_ms"' logs/app.log | awk -F'"duration_ms":' '{print $2}' | sort -n

# Count requests by path
grep '"path":' logs/app.log | cut -d'"' -f8 | sort | uniq -c
```

## Best Practices

### 1. Always Log with Context

❌ **Bad**:
```python
logger.info("Processing request")
```

✅ **Good**:
```python
logger.info("Processing interview request", extra={
    "user_id": user_id,
    "session_id": session_id,
    "interview_type": interview_type,
    "request_id": request_id
})
```

### 2. Use Appropriate Log Levels

- **DEBUG**: Development details, verbose data
- **INFO**: Business logic flow, successful operations
- **WARNING**: Recoverable issues, degraded performance
- **ERROR**: Errors requiring attention
- **CRITICAL**: System failures

### 3. Sanitize Sensitive Data

Always remove:
- Passwords
- API keys
- Tokens
- Credit card numbers
- SSN
- Personal health information

```python
# Automatically done in monitoring module
safe_data = sanitize_sensitive_fields(data)
logger.info("User data", extra=safe_data)
```

### 4. Track Performance

For any operation > 100ms:
```python
with track_time("slow_operation", {"user_id": 123}):
    result = await slow_operation()
```

### 5. Add Breadcrumbs

Help debug issues by adding breadcrumbs:
```python
add_breadcrumb("Fetch user profile", category="database", data={"user_id": 123})
add_breadcrumb("Build RAG context", category="ai", data={"doc_count": 15})
add_breadcrumb("Generate response", category="ai", data={"tokens": 500})
# If error occurs, see full trail in Sentry
```

## Debugging Workflow

### 1. Find Error in Logs

```bash
grep -A 10 "ERROR" logs/app.log | tail -n 50
```

### 2. Get Request ID

```
"request_id": "abc-123-def"
```

### 3. Track All Logs for Request

```bash
grep "abc-123-def" logs/app.log
```

### 4. View in Sentry

Search: `request_id:"abc-123-def"`

See:
- Full error context
- Breadcrumb trail
- User context
- Performance data

### 5. View in LangSmith (for AI operations)

- Find trace URL in logs
- View conversation flow
- Check token usage
- Identify bottlenecks

## Example: Complete Logging Flow

```python
from app.core.monitoring import (
    track_time,
    log_step,
    log_metric,
    log_function_call,
    log_user_action
)
from app.core.sentry import add_breadcrumb, set_context

@log_function_call(level="info", track_performance=True)
async def process_interview_session(user_id: int, session_id: int):
    """Complete example with comprehensive logging."""

    # Set context for error tracking
    set_context("interview_context", {
        "user_id": user_id,
        "session_id": session_id
    })

    # Step 1: Fetch data
    log_step("Fetch Interview Data", {
        "user_id": user_id,
        "session_id": session_id
    })

    add_breadcrumb("Fetch session data", category="database")

    with track_time("fetch_session", {"session_id": session_id}):
        session = await get_session(session_id)

    # Step 2: Process
    log_step("Process Responses", {
        "interaction_count": len(session.interactions)
    })

    with track_time("generate_assessment"):
        assessment = await generate_assessment(session)

    # Step 3: Log metrics
    log_metric("assessment_score", assessment.overall_score)
    log_metric("assessment_generated", 1, {
        "interview_type": session.interview_type,
        "user_id": str(user_id)
    })

    # Step 4: Log user action
    log_user_action(
        user_id=user_id,
        action="interview_completed",
        details={
            "session_id": session_id,
            "score": assessment.overall_score
        }
    )

    log_step("Assessment Complete", {
        "status": "success",
        "overall_score": assessment.overall_score
    })

    return assessment
```

## Performance Impact

Logging overhead is minimal:
- Structured logging: ~0.1-0.5ms per log
- Sentry breadcrumbs: ~0.01ms per breadcrumb
- Sentry spans: ~0.1ms per span
- Metrics: ~0.01ms per metric

Total overhead: **< 1% of request time**

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% of traces
SENTRY_PROFILES_SAMPLE_RATE=1.0  # 100% of profiles

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxx
LANGCHAIN_PROJECT=genai-mock-interview
```

### Adjusting Log Levels

**Development**:
```bash
LOG_LEVEL=DEBUG
```

**Production**:
```bash
LOG_LEVEL=INFO  # or WARNING
```

## Troubleshooting

### Logs Not Appearing

1. Check log level: `LOG_LEVEL=DEBUG`
2. Check file permissions on `logs/` directory
3. Verify logging setup in `app/main.py`

### Sentry Not Capturing Errors

1. Verify `SENTRY_DSN` is set
2. Check `SENTRY_ENVIRONMENT`
3. Ensure `init_sentry()` is called
4. Check network connectivity

### LangSmith Traces Missing

1. Set `LANGCHAIN_TRACING_V2=true`
2. Provide `LANGCHAIN_API_KEY`
3. Restart application
4. Check LangSmith project name

## Summary

The comprehensive logging and monitoring system provides:

✅ **Full Request Tracking**: Every request logged with unique ID
✅ **Performance Monitoring**: Automatic timing of all operations
✅ **Error Tracking**: Complete error context in Sentry
✅ **AI Observability**: Full LLM traces in LangSmith
✅ **Metrics Collection**: Business and technical metrics
✅ **User Analytics**: Track user actions and behavior
✅ **Debugging Tools**: Breadcrumbs, context, and correlation

---

**For more information**:
- Sentry Dashboard: https://sentry.io
- LangSmith Dashboard: https://smith.langchain.com
- Log files: `logs/app.log`
