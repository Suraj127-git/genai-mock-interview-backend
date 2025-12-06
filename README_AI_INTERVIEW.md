# AI-Powered Mock Interview System

A comprehensive AI-powered interview coaching system built with FastAPI, LangChain, and LangGraph. Features RAG-based personalization, multi-dimensional assessment, real-time audio/video analysis, and extensive observability.

## Features

### Core Functionality
- **Intelligent Conversation**: AI-powered interview sessions using Groq's Llama 3.3 70B model
- **Personalized Experience**: RAG system retrieves user context for tailored questions
- **Multi-dimensional Scoring**: 20+ scoring dimensions across communication, content, and behavioral aspects
- **Real-time Analysis**: Audio/video analysis with LiveKit integration
- **Comprehensive Feedback**: Actionable recommendations with strengths and areas for improvement

### Technology Stack
- **Backend**: FastAPI with async/await support
- **AI Orchestration**: LangChain + LangGraph for workflow management
- **LLM Provider**: Groq (primary), OpenAI (fallback)
- **Vector Database**: ChromaDB with sentence-transformers embeddings
- **Observability**: LangSmith for full tracing and monitoring
- **Database**: MySQL with SQLAlchemy async ORM
- **Real-time**: LiveKit for audio/video communication

### Third-party Integrations
- **LiveKit**: Real-time audio/video
- **Cartesia**: Advanced speech analysis
- **Murf**: Text-to-speech generation
- **Exa/Serper/Tavily**: Web search for RAG enhancement

## Architecture

### Components

```
app/
├── services/
│   ├── rag_service.py              # RAG system for user context retrieval
│   ├── langgraph_interview_service.py   # LangGraph workflow orchestration
│   ├── assessment_service.py       # Multi-dimensional scoring engine
│   └── third_party_tools.py        # Tool integrations (LiveKit, etc.)
├── models/
│   ├── user_profile.py             # User profile with RAG context
│   ├── ai_interview_session.py     # Interview session tracking
│   └── ai_interview_interaction.py # Conversation history
├── api/endpoints/
│   └── ai_interview.py             # REST API endpoints
└── middleware/
    └── rate_limiter.py             # API rate limiting
```

### Workflow

1. **User Profile Creation**: Store user background, skills, and preferences
2. **RAG Indexing**: Index profile into vector database for retrieval
3. **Interview Start**: LangGraph orchestrates personalized interview
4. **Real-time Interaction**: Multi-turn conversation with context awareness
5. **Assessment**: Comprehensive scoring across multiple dimensions
6. **Feedback**: Detailed recommendations and next steps

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required
GROQ_API_KEY=gsk_your-key
SECRET_KEY=your-secret-key
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/genai_coach

# Recommended
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_your-key
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload
```

### 5. Access API Documentation

Visit http://localhost:8000/docs

## API Usage

### Create User Profile

```bash
curl -X POST http://localhost:8000/ai-interview/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_role": "Software Engineer",
    "years_of_experience": 5,
    "target_role": "Senior Software Engineer",
    "technical_skills": ["Python", "React", "AWS"],
    "bio": "Full-stack engineer specializing in backend development"
  }'
```

### Start Interview

```bash
curl -X POST http://localhost:8000/ai-interview/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Technical Interview Practice",
    "interview_type": "technical",
    "difficulty_level": "hard",
    "role_context": "Senior Software Engineer"
  }'
```

Response includes first AI question:
```json
{
  "session_id": 123,
  "response": "Hello! I see you're a Software Engineer with 5 years of experience preparing for a Senior role. Let's begin with a system design question...",
  "status": "active"
}
```

### Send Response

```bash
curl -X POST http://localhost:8000/ai-interview/sessions/123/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I would design a distributed caching system using Redis..."
  }'
```

### Complete & Get Assessment

```bash
curl -X POST http://localhost:8000/ai-interview/sessions/123/complete \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Returns comprehensive assessment with scores and feedback.

## Scoring System

### Dimensions (0-100 scale)

**Communication (30% weight)**
- Verbal clarity and articulation
- Confidence level
- Speaking pace (words per minute analysis)

**Content (50% weight)**
- Technical accuracy
- Problem-solving approach
- Response structure
- Relevance to questions

**Behavioral (20% weight)**
- STAR method usage (Situation-Task-Action-Result)
- Leadership demonstration
- Teamwork examples

**Non-verbal (if video available)**
- Eye contact
- Body language
- Engagement level

### Overall Score Calculation

```python
overall_score = (
    communication_avg * 0.30 +
    content_avg * 0.50 +
    behavioral_avg * 0.20
)
```

## RAG System

### How It Works

1. **Indexing**: User profiles and interview history stored in ChromaDB
2. **Retrieval**: Semantic search retrieves relevant context for each interview
3. **Personalization**: LLM uses retrieved context to tailor questions and feedback

### Example Context

```
User: john@example.com
Currently: Software Engineer at Tech Corp (5 years experience)
Target: Senior Software Engineer at Google
Skills: Python, React, AWS, Docker, Kubernetes
Previous Feedback: "Needs more system design practice"
```

LLM uses this to:
- Ask relevant technical questions
- Reference past experience
- Target areas for improvement
- Provide personalized feedback

## LangGraph Workflow

### State Machine

```
┌─────────────────┐
│ Prepare Context │ (RAG retrieval)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Conduct Interview│ (Generate questions)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Analyze Response │ (Speech metrics, sentiment)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Check Completion │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
continue    end
    │         │
    │         ▼
    │   ┌─────────────────┐
    │   │Generate Feedback│
    │   └─────────────────┘
    │
    └──► (loop back)
```

### Tool Calling

LangGraph can invoke external tools:
- **LiveKit**: Create rooms, generate tokens
- **Cartesia**: Analyze speech patterns
- **Murf**: Generate AI voice responses
- **Search APIs**: Fetch industry-specific information

## LangSmith Observability

### What's Tracked

- Full conversation traces
- LLM calls and responses
- Token usage per interview
- Latency metrics
- Error traces
- Tool invocations

### Access Traces

1. Enable in `.env`:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_...
   ```

2. View at https://smith.langchain.com

3. Each session includes `langsmith_trace_url` for quick access

## Rate Limiting

### Limits

| Endpoint | Limit |
|----------|-------|
| Start Interview | 10/min |
| Send Message | 30/min |
| Chat | 20/min |
| Login | 5/min |
| Register | 3/min |

### Response Headers

```
X-RateLimit-Limit: 10
X-RateLimit-Window: 60
```

## Testing

### Run Tests

```bash
# All tests
pytest -v

# AI Interview tests only
pytest -m ai_interview -v

# With coverage
pytest --cov=app tests/ --cov-report=html
```

### Test Categories

- Profile management
- Interview sessions
- Message handling
- Assessment generation
- Authorization
- Rate limiting

## Deployment

### Railway

```bash
railway init
railway add # Select MySQL
railway variables set GROQ_API_KEY="gsk_..."
railway up
```

### Docker

```bash
docker-compose up -d
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

## Documentation

- **API Reference**: [AI_INTERVIEW_API.md](AI_INTERVIEW_API.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Main README**: [CLAUDE.md](CLAUDE.md)

## API Keys Required

### Essential
- **Groq**: Fast LLM inference (https://console.groq.com)
- **Database**: MySQL connection

### Highly Recommended
- **LangSmith**: Observability (https://smith.langchain.com)

### Optional
- **LiveKit**: Real-time audio/video (https://livekit.io)
- **Cartesia**: Speech analysis (https://cartesia.ai)
- **Murf**: Text-to-speech (https://murf.ai)
- **Search APIs**: Exa, Serper, or Tavily

## Performance

### Typical Response Times
- Profile creation: ~200ms
- Start interview: ~1-2s (includes RAG retrieval + LLM call)
- Send message: ~1-2s
- Complete assessment: ~3-5s (comprehensive analysis)

### Optimization Tips
1. Use Groq for fast LLM inference
2. Index user profiles immediately after creation
3. Enable Redis caching for production
4. Monitor LangSmith for bottlenecks

## Security

- JWT authentication on all endpoints
- Rate limiting to prevent abuse
- SQL injection protection via SQLAlchemy
- API key encryption
- CORS configuration
- Input validation with Pydantic

## Troubleshooting

### LLM Not Responding
- Check `GROQ_API_KEY` is valid
- View LangSmith traces for errors
- Fallback to OpenAI if Groq unavailable

### RAG Not Working
- Verify ChromaDB directory exists
- Re-index user profile: `POST /ai-interview/profile/index`
- Check embeddings model is downloaded

### Database Issues
- Verify `DATABASE_URL` format: `mysql+aiomysql://...`
- Run migrations: `alembic upgrade head`
- Check connection pooling settings

## Contributing

1. Create feature branch
2. Write tests for new features
3. Ensure tests pass: `pytest`
4. Update documentation
5. Submit pull request

## License

Copyright © 2025 GenAI Coach. All rights reserved.

## Support

For issues or questions:
- Check LangSmith traces
- Review application logs
- Open GitHub issue with details
