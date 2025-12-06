# AI Interview System - Deployment Guide

## Prerequisites

- Python 3.11+
- MySQL 8.0+
- Redis (optional, for production rate limiting)
- API keys for third-party services

## Installation

### 1. Install Dependencies

```bash
cd genai-mock-interview-backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/genai_coach

# Security
SECRET_KEY=your-secret-key-min-32-chars-long-very-secure

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# OpenAI (fallback LLM)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Groq (primary LLM - faster and cheaper)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# LangSmith (Observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=genai-mock-interview

# LiveKit (Real-time Communication)
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-livekit-server.com

# Optional: Speech Analysis
CARTESIA_API_KEY=your-cartesia-key
MURF_API_KEY=your-murf-key

# Optional: Search Services
EXA_API_KEY=your-exa-key
SERPER_API_KEY=your-serper-key
TAVILY_API_KEY=your-tavily-key

# Vector Database
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Application
ENVIRONMENT=development
DEBUG=True
CORS_ORIGINS=http://localhost:8081,http://localhost:3000

# Logging
LOG_LEVEL=INFO

# Sentry (Optional)
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
```

### 3. Database Setup

```bash
# Create database
mysql -u root -p
CREATE DATABASE genai_coach CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;

# Run migrations
alembic upgrade head

# Verify migrations
alembic current
```

### 4. Initialize Vector Database

The ChromaDB vector database will be initialized automatically on first use. Ensure the `CHROMA_PERSIST_DIR` directory exists:

```bash
mkdir -p chroma_db
```

### 5. Start the Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Key Setup

### Groq API (Required)

1. Sign up at https://console.groq.com
2. Create API key
3. Add to `.env` as `GROQ_API_KEY`

**Why Groq?**
- Fast inference (up to 10x faster than other providers)
- Cost-effective
- Supports Llama 3.3 70B model
- Good balance of speed and quality

### LangSmith (Highly Recommended)

1. Sign up at https://smith.langchain.com
2. Create project
3. Get API key from settings
4. Add to `.env`:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_...
   LANGCHAIN_PROJECT=genai-mock-interview
   ```

**Benefits:**
- Full tracing of all AI operations
- Debug conversation flows
- Monitor token usage and costs
- Performance analytics

### LiveKit (Optional, for Real-time Audio/Video)

1. Sign up at https://livekit.io or deploy self-hosted
2. Create project and get credentials
3. Add to `.env`:
   ```
   LIVEKIT_API_KEY=...
   LIVEKIT_API_SECRET=...
   LIVEKIT_URL=wss://...
   ```

**Use Cases:**
- Real-time video interviews with facial analysis
- Live audio feedback
- Multi-participant interview scenarios

### Other Optional Services

**Cartesia** (Speech Analysis):
- Sign up at https://cartesia.ai
- Advanced prosody and emotion analysis

**Murf** (Text-to-Speech):
- Sign up at https://murf.ai
- Natural AI voice for interview questions

**Search APIs** (for RAG enhancement):
- **Exa**: https://exa.ai - Semantic search
- **Serper**: https://serper.dev - Google search API
- **Tavily**: https://tavily.com - Research-focused search

## Database Migrations

### Creating New Migrations

After modifying models in `app/models/`:

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Description of changes"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

### Common Migration Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade one revision
alembic downgrade -1

# Downgrade to base
alembic downgrade base
```

## Testing

### Run All Tests

```bash
cd tests
pytest -v
```

### Run Specific Test Categories

```bash
# AI Interview tests only
pytest -m ai_interview -v

# Authentication tests
pytest -m auth -v

# All tests with coverage
pytest --cov=app tests/ --cov-report=html
```

### Test Configuration

Tests use the production Railway API by default. To use local:

1. Update `tests/conftest.py`
2. Change `BASE_URL` to `http://localhost:8000`

## Production Deployment

### Railway Deployment

1. **Create Railway Project**
   ```bash
   railway login
   railway init
   ```

2. **Add MySQL Plugin**
   ```bash
   railway add
   # Select MySQL
   ```

3. **Set Environment Variables**
   ```bash
   railway variables set SECRET_KEY="your-secret-key"
   railway variables set GROQ_API_KEY="gsk_..."
   railway variables set LANGCHAIN_API_KEY="lsv2_..."
   railway variables set LANGCHAIN_TRACING_V2="true"
   # ... set all other required variables
   ```

4. **Deploy**
   ```bash
   railway up
   ```

5. **Run Migrations**
   ```bash
   railway run alembic upgrade head
   ```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start server
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://user:password@db:3306/genai_coach
      - SECRET_KEY=${SECRET_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: mysql:8.0
    environment:
      - MYSQL_DATABASE=genai_coach
      - MYSQL_ROOT_PASSWORD=rootpassword
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  mysql_data:
```

Run with:
```bash
docker-compose up -d
```

## Monitoring & Observability

### LangSmith Dashboard

Access at https://smith.langchain.com

**Key Metrics to Monitor:**
- Request latency
- Token usage per interview
- Error rates
- Most common questions
- User engagement patterns

### Sentry Error Tracking

If configured, access at your Sentry dashboard.

**Monitored Events:**
- API errors
- LLM failures
- Database connection issues
- Rate limit violations

### Application Logs

Logs are structured JSON for easy parsing:

```bash
# View logs
tail -f logs/app.log

# Filter errors
grep "ERROR" logs/app.log

# Filter AI operations
grep "ai" logs/app.log
```

## Performance Optimization

### Vector Database Optimization

```python
# Periodically rebuild index for better performance
from app.services.rag_service import RAGService

rag_service = RAGService()
# Re-index all users
for user_id in active_users:
    await rag_service.index_user_context(db, user_id)
```

### Database Connection Pooling

Already configured in `app/db/base.py`:
- Pool size: 10
- Max overflow: 20
- Pool recycle: 3600 seconds

### Caching

For production, implement Redis caching:

```python
# Cache user profiles
@cached(ttl=3600)
async def get_user_profile(user_id: int):
    # ...
```

## Backup & Recovery

### Database Backups

```bash
# Backup
mysqldump -u user -p genai_coach > backup_$(date +%Y%m%d).sql

# Restore
mysql -u user -p genai_coach < backup_20251207.sql
```

### Vector Database Backups

```bash
# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/

# Restore
tar -xzf chroma_backup_20251207.tar.gz
```

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Check DATABASE_URL format
# Should be: mysql+aiomysql://user:pass@host:port/db

# Test connection
python -c "from app.db.base import get_db; print('OK')"
```

**2. LLM API Errors**
```bash
# Verify API keys
echo $GROQ_API_KEY

# Check LangSmith traces for detailed errors
```

**3. Vector Database Issues**
```bash
# Clear and rebuild
rm -rf chroma_db/
mkdir chroma_db
# Restart server to reinitialize
```

**4. Migration Conflicts**
```bash
# Reset to clean state (DEV ONLY!)
alembic downgrade base
alembic upgrade head
```

## Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Use strong database passwords
- [ ] Enable HTTPS in production
- [ ] Set `DEBUG=False` in production
- [ ] Configure CORS properly
- [ ] Implement rate limiting (already included)
- [ ] Regular security updates: `pip list --outdated`
- [ ] Monitor Sentry for security issues
- [ ] Rotate API keys regularly
- [ ] Enable database encryption at rest

## Scaling

### Horizontal Scaling

Deploy multiple instances behind a load balancer:

```bash
# Start multiple workers
uvicorn app.main:app --workers 4
```

### Vertical Scaling

Recommended minimum specs:
- **Development**: 2 CPU, 4GB RAM
- **Production**: 4 CPU, 8GB RAM, 50GB SSD

### Database Scaling

- Enable MySQL read replicas
- Implement query caching
- Index frequently queried columns

## Support

For issues or questions:
1. Check LangSmith traces for AI-related issues
2. Review application logs
3. Check Sentry for error reports
4. Open GitHub issue with logs and environment details
