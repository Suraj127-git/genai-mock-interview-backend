# AI Interview API Documentation

## Overview

The AI Interview API provides a comprehensive AI-powered mock interview system with the following features:

- **RAG-based personalization**: Retrieves user context for personalized interview experiences
- **Multi-dimensional assessment**: Scores candidates across communication, content, and behavioral dimensions
- **Real-time interaction**: Supports audio/video analysis via LiveKit integration
- **LangChain/LangGraph orchestration**: Advanced workflow management with tool calling
- **LangSmith observability**: Full tracing and monitoring of AI operations

## Architecture

### Core Components

1. **RAG Service** (`rag_service.py`)
   - Indexes user profiles and interview history into vector database (ChromaDB)
   - Retrieves relevant context for personalized interview prompts
   - Uses sentence-transformers for embeddings

2. **LangGraph Interview Service** (`langgraph_interview_service.py`)
   - Orchestrates interview workflow using LangGraph state machines
   - Manages multi-turn conversations with context awareness
   - Integrates with Groq LLM for fast responses

3. **Assessment Service** (`assessment_service.py`)
   - Performs comprehensive multi-dimensional scoring
   - Analyzes communication, content, and behavioral aspects
   - Generates detailed feedback with actionable recommendations

4. **Third-party Tools** (`third_party_tools.py`)
   - LiveKit: Real-time audio/video communication
   - Cartesia: Advanced speech analysis
   - Murf: Text-to-speech generation
   - Exa/Serper/Tavily: Web search capabilities

### Database Models

#### UserProfile
Stores user context for RAG retrieval:
- Professional information (role, company, experience)
- Skills (technical and soft skills)
- Education and certifications
- Interview preferences
- Resume text and bio

#### AIInterviewSession
Tracks complete interview sessions:
- Session metadata (title, type, status)
- Multi-dimensional scores (20+ different metrics)
- Detailed feedback and recommendations
- LangSmith trace information

#### AIInterviewInteraction
Stores individual messages/turns:
- Message content and role
- Timing and response metrics
- Speech analysis (WPM, filler words, sentiment)
- Tool call results

## API Endpoints

### User Profile Management

#### Create Profile
```http
POST /ai-interview/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_role": "Software Engineer",
  "current_company": "Tech Corp",
  "years_of_experience": 5,
  "target_role": "Senior Software Engineer",
  "target_companies": ["Google", "Meta"],
  "technical_skills": ["Python", "React", "AWS"],
  "soft_skills": ["Leadership", "Communication"],
  "difficulty_preference": "medium",
  "bio": "Experienced software engineer specializing in full-stack development"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "user_id": 123,
  "current_role": "Software Engineer",
  "target_role": "Senior Software Engineer",
  "created_at": "2025-12-07T10:00:00Z"
}
```

#### Get Profile
```http
GET /ai-interview/profile
Authorization: Bearer {token}
```

#### Update Profile
```http
PUT /ai-interview/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "years_of_experience": 6,
  "technical_skills": ["Python", "React", "AWS", "Kubernetes"]
}
```

#### Index Profile (RAG)
```http
POST /ai-interview/profile/index
Authorization: Bearer {token}
```

Manually trigger RAG indexing of user profile and interview history.

### Interview Sessions

#### Start Interview
```http
POST /ai-interview/sessions
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Technical Interview Practice",
  "interview_type": "technical",
  "role_context": "Senior Software Engineer",
  "company_context": "Google",
  "difficulty_level": "hard",
  "custom_instructions": "Focus on system design and scalability"
}
```

**Interview Types**:
- `behavioral` - STAR method, leadership, teamwork
- `technical` - Coding, algorithms, system design
- `case` - Business case analysis
- `system_design` - Architecture and scalability
- `general` - Mixed interview questions

**Response**: `201 Created`
```json
{
  "session_id": 456,
  "message": "Interview started successfully",
  "response": "Hello! I'm excited to conduct this technical interview with you today. I see you're a Software Engineer with 5 years of experience, preparing for a Senior Software Engineer role at Google. Let's begin with a system design question...",
  "status": "active",
  "question_count": 0
}
```

#### Send Message
```http
POST /ai-interview/sessions/{session_id}/message
Authorization: Bearer {token}
Content-Type: application/json

{
  "message": "I would design a distributed caching system using Redis...",
  "audio_s3_key": "optional-audio-recording-key",
  "audio_duration_seconds": 120.5
}
```

**Response**: `200 OK`
```json
{
  "session_id": 456,
  "response": "That's a great start! Can you explain how you would handle cache invalidation in a distributed environment?",
  "status": "active",
  "question_count": 1,
  "analysis": {
    "question_1": {
      "response_length": 250,
      "word_count": 45,
      "timestamp": "2025-12-07T10:05:00Z"
    }
  }
}
```

#### Complete Interview
```http
POST /ai-interview/sessions/{session_id}/complete
Authorization: Bearer {token}
```

Ends the interview and triggers comprehensive assessment.

**Response**: `200 OK`
```json
{
  "id": 456,
  "status": "completed",
  "overall_score": 82.5,
  "verbal_communication_score": 85.0,
  "clarity_score": 88.0,
  "confidence_score": 82.0,
  "technical_accuracy_score": 90.0,
  "problem_solving_score": 80.0,
  "strengths": {
    "strengths": [
      "Strong technical foundation",
      "Clear and structured responses",
      "Good understanding of distributed systems"
    ]
  },
  "weaknesses": {
    "weaknesses": [
      "Could provide more concrete examples",
      "Consider edge cases more thoroughly"
    ]
  },
  "detailed_feedback": "Overall excellent performance. Your technical knowledge is strong and you communicate concepts clearly. Focus on providing more real-world examples and considering edge cases in your solutions.",
  "completed_at": "2025-12-07T10:30:00Z"
}
```

#### List Sessions
```http
GET /ai-interview/sessions?skip=0&limit=20
Authorization: Bearer {token}
```

#### Get Session Details
```http
GET /ai-interview/sessions/{session_id}
Authorization: Bearer {token}
```

Returns session with full conversation history (interactions).

#### Assess Session
```http
POST /ai-interview/sessions/{session_id}/assess
Authorization: Bearer {token}
```

Generate or re-generate assessment for a session.

**Response**: `200 OK`
```json
{
  "session_id": 456,
  "overall_score": 82.5,
  "communication_scores": {
    "verbal_communication_score": 85.0,
    "clarity_score": 88.0,
    "confidence_score": 82.0,
    "pace_score": 84.0,
    "words_per_minute": 145,
    "filler_word_count": 3
  },
  "content_scores": {
    "technical_accuracy_score": 90.0,
    "problem_solving_score": 80.0,
    "structure_score": 85.0,
    "relevance_score": 88.0
  },
  "behavioral_scores": {
    "star_method_score": null,
    "leadership_score": null,
    "teamwork_score": null
  },
  "feedback": {
    "strengths": ["Strong technical foundation", "Clear communication"],
    "weaknesses": ["Could provide more examples"],
    "detailed_feedback": "Excellent performance overall...",
    "next_steps": ["Practice system design patterns", "Study distributed systems"],
    "recommended_topics": ["CAP theorem", "Consistent hashing"]
  },
  "assessed_at": "2025-12-07T10:35:00Z"
}
```

### LiveKit Integration

#### Get LiveKit Token
```http
POST /ai-interview/livekit/token?room_name=interview-room-456&participant_name=John
Authorization: Bearer {token}
```

Generates access token for real-time audio/video communication.

**Response**: `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "room_name": "interview-room-456",
  "participant_name": "John",
  "url": "wss://livekit.example.com",
  "expires_at": "2025-12-07T11:00:00Z"
}
```

## Scoring Dimensions

### Communication Scores (30% weight)
- **Verbal Communication**: Overall clarity and articulation
- **Clarity**: How clear and understandable responses are
- **Confidence**: Confidence level demonstrated
- **Pace**: Speaking pace appropriateness (WPM analysis)

### Content Scores (50% weight)
- **Technical Accuracy**: Correctness of answers
- **Problem Solving**: Approach to solving problems
- **Structure**: Organization of responses
- **Relevance**: How relevant answers are to questions

### Behavioral Scores (20% weight)
- **STAR Method**: Use of Situation-Task-Action-Result framework
- **Leadership**: Leadership qualities demonstrated
- **Teamwork**: Collaboration and teamwork examples

### Non-verbal Scores (if video available)
- **Eye Contact**: Eye contact maintenance
- **Body Language**: Posture and gestures
- **Engagement**: Overall engagement level

## Environment Variables

Add these to your `.env` file:

```bash
# LangChain/LangGraph
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# LangSmith (Observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=genai-mock-interview

# LiveKit (Real-time Audio/Video)
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
LIVEKIT_URL=wss://your-livekit-url

# Third-party AI Services (Optional)
CARTESIA_API_KEY=your-key
MURF_API_KEY=your-key

# Search Services (Optional, for RAG enhancement)
EXA_API_KEY=your-key
SERPER_API_KEY=your-key
TAVILY_API_KEY=your-key

# Vector Database
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- `/ai-interview/sessions`: 10 requests/minute
- `/ai-interview/sessions/{id}/message`: 30 requests/minute
- `/ai/chat`: 20 requests/minute
- `/auth/login`: 5 requests/minute
- `/auth/register`: 3 requests/minute
- Default: 60 requests/minute

Rate limit headers in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Window`: Time window in seconds
- `Retry-After`: Seconds to wait before retrying (on 429 errors)

## Error Handling

All endpoints return standard error responses:

```json
{
  "detail": "Error description",
  "error_code": "OPTIONAL_ERROR_CODE"
}
```

**Common HTTP Status Codes**:
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

## LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true`, all AI operations are traced in LangSmith:

- View traces at: https://smith.langchain.com
- Each interview session includes:
  - Full conversation history
  - LLM calls and responses
  - Tool invocations
  - Timing and token usage
  - Error traces

Access trace URL from session:
```json
{
  "langsmith_run_id": "abc123",
  "langsmith_trace_url": "https://smith.langchain.com/public/abc123/r"
}
```

## Database Migrations

After adding new models, create and run migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add AI interview models"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Testing

Run tests for AI interview endpoints:

```bash
cd tests
pytest test_ai_interview.py -v
pytest test_ai_interview.py::TestAIInterview::test_create_profile -v
```

## Best Practices

1. **Always index user profile** after creation/update for best RAG performance
2. **Complete interviews** to trigger full assessment (don't leave sessions hanging)
3. **Use appropriate interview types** for accurate scoring
4. **Provide context** (role, company) for more personalized interviews
5. **Monitor LangSmith** for debugging and optimization
6. **Respect rate limits** to avoid throttling

## Future Enhancements

- Real-time video analysis using computer vision
- Support for multiple languages
- Custom scoring rubrics per interview type
- Integration with ATS systems
- Interview recording playback
- Peer comparison analytics
