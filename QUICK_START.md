# Quick Start Guide - AI Interview System

Get the AI-powered interview system running in 5 minutes.

## Prerequisites
- Python 3.11+
- MySQL 8.0+
- Groq API key ([Get one free](https://console.groq.com))

## Installation

### 1. Clone & Setup
```bash
cd genai-mock-interview-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example config
cp .env.example .env

# Edit .env - minimum required:
# DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/genai_coach
# SECRET_KEY=your-secret-key-min-32-chars
# GROQ_API_KEY=gsk_your-key-from-groq-console
```

### 3. Setup Database
```bash
# Create database
mysql -u root -p -e "CREATE DATABASE genai_coach"

# Run migrations
alembic upgrade head
```

### 4. Start Server
```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

## Quick Test

### 1. Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "name": "Test User"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=test@example.com&password=TestPass123!"
```

Save the `access_token` from response.

### 3. Create Profile
```bash
curl -X POST http://localhost:8000/ai-interview/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_role": "Software Engineer",
    "years_of_experience": 3,
    "target_role": "Senior Engineer",
    "technical_skills": ["Python", "JavaScript", "React"]
  }'
```

### 4. Start Interview
```bash
curl -X POST http://localhost:8000/ai-interview/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Interview",
    "interview_type": "technical"
  }'
```

You'll receive an AI-generated introduction and first question!

## Optional: Enable LangSmith Tracing

1. Sign up at https://smith.langchain.com (free tier available)
2. Create project and get API key
3. Add to `.env`:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_your-key
LANGCHAIN_PROJECT=genai-mock-interview
```

View all AI operations in real-time at https://smith.langchain.com

## Common Commands

```bash
# Start development server
uvicorn app.main:app --reload

# Run tests
pytest -v

# Run specific test
pytest tests/test_ai_interview.py -v

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# View current migration
alembic current
```

## Troubleshooting

**Can't connect to database?**
```bash
# Check MySQL is running
mysql -u root -p -e "SHOW DATABASES"

# Verify DATABASE_URL format in .env
# Should be: mysql+aiomysql://user:password@host:port/dbname
```

**Groq API errors?**
```bash
# Verify key in .env
echo $GROQ_API_KEY

# Test with curl
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer YOUR_KEY"
```

**Import errors?**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Next Steps

- Read [AI_INTERVIEW_API.md](AI_INTERVIEW_API.md) for full API reference
- Check [README_AI_INTERVIEW.md](README_AI_INTERVIEW.md) for architecture details
- See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production deployment

## Key Files

- **API Docs**: http://localhost:8000/docs (interactive)
- **Configuration**: `.env` file
- **Database Models**: `app/models/`
- **API Endpoints**: `app/api/endpoints/ai_interview.py`
- **Services**: `app/services/`

## Support

Questions? Check:
1. API documentation at `/docs`
2. LangSmith traces (if enabled)
3. Application logs
4. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) troubleshooting section

Happy interviewing! 🚀
