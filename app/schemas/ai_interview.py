"""
Pydantic schemas for AI interview endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Request Schemas
class UserProfileCreate(BaseModel):
    """Schema for creating user profile."""
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    target_role: Optional[str] = None
    target_companies: Optional[List[str]] = None
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    interview_types: Optional[List[str]] = None
    difficulty_preference: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    resume_text: Optional[str] = None
    bio: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    target_role: Optional[str] = None
    target_companies: Optional[List[str]] = None
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    interview_types: Optional[List[str]] = None
    difficulty_preference: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    resume_text: Optional[str] = None
    bio: Optional[str] = None


class AIInterviewSessionCreate(BaseModel):
    """Schema for creating AI interview session."""
    title: str = Field(..., min_length=1, max_length=255)
    interview_type: str = Field(default="general")
    role_context: Optional[str] = None
    company_context: Optional[str] = None
    difficulty_level: Optional[str] = Field(default="medium")
    custom_instructions: Optional[str] = None


class AIInterviewMessageSend(BaseModel):
    """Schema for sending message in AI interview."""
    message: str = Field(..., min_length=1)
    audio_s3_key: Optional[str] = None
    audio_duration_seconds: Optional[float] = None


class AIInterviewSessionComplete(BaseModel):
    """Schema for completing AI interview session."""
    session_id: int


# Response Schemas
class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    id: int
    user_id: int
    current_role: Optional[str]
    current_company: Optional[str]
    years_of_experience: Optional[int]
    target_role: Optional[str]
    target_companies: Optional[Dict[str, Any]]
    technical_skills: Optional[Dict[str, Any]]
    soft_skills: Optional[Dict[str, Any]]
    industries: Optional[Dict[str, Any]]
    education: Optional[Dict[str, Any]]
    certifications: Optional[Dict[str, Any]]
    interview_types: Optional[Dict[str, Any]]
    difficulty_preference: Optional[str]
    focus_areas: Optional[Dict[str, Any]]
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIInterviewInteractionResponse(BaseModel):
    """Schema for AI interview interaction response."""
    id: int
    session_id: int
    role: str
    content: str
    timestamp: datetime
    response_time_seconds: Optional[float]
    words_per_minute: Optional[float]
    filler_word_count: Optional[int]
    sentiment_score: Optional[float]

    class Config:
        from_attributes = True


class AIInterviewSessionResponse(BaseModel):
    """Schema for AI interview session response."""
    id: int
    user_id: int
    title: str
    interview_type: str
    status: str
    role_context: Optional[str]
    company_context: Optional[str]
    difficulty_level: Optional[str]
    duration_seconds: Optional[int]
    overall_score: Optional[float]
    verbal_communication_score: Optional[float]
    clarity_score: Optional[float]
    confidence_score: Optional[float]
    pace_score: Optional[float]
    technical_accuracy_score: Optional[float]
    problem_solving_score: Optional[float]
    structure_score: Optional[float]
    relevance_score: Optional[float]
    star_method_score: Optional[float]
    leadership_score: Optional[float]
    teamwork_score: Optional[float]
    strengths: Optional[Dict[str, Any]]
    weaknesses: Optional[Dict[str, Any]]
    improvements: Optional[Dict[str, Any]]
    detailed_feedback: Optional[str]
    recommended_topics: Optional[Dict[str, Any]]
    next_steps: Optional[Dict[str, Any]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIInterviewSessionDetailResponse(AIInterviewSessionResponse):
    """Schema for detailed AI interview session response with interactions."""
    interactions: List[AIInterviewInteractionResponse] = []


class AIInterviewStartResponse(BaseModel):
    """Schema for starting AI interview response."""
    session_id: int
    message: str
    response: str
    status: str
    question_count: int


class AIInterviewMessageResponse(BaseModel):
    """Schema for AI interview message response."""
    session_id: int
    response: str
    status: str
    question_count: int
    analysis: Optional[Dict[str, Any]] = None


class AIInterviewAssessmentResponse(BaseModel):
    """Schema for AI interview assessment response."""
    session_id: int
    overall_score: float
    communication_scores: Dict[str, Any]
    content_scores: Dict[str, Any]
    behavioral_scores: Dict[str, Any]
    feedback: Dict[str, Any]
    assessed_at: str


class RAGIndexResponse(BaseModel):
    """Schema for RAG indexing response."""
    success: bool
    user_id: int
    documents_indexed: int
    message: str


class LiveKitTokenResponse(BaseModel):
    """Schema for LiveKit token response."""
    token: str
    room_name: str
    participant_name: str
    url: str
    expires_at: Optional[datetime] = None
