"""
AI-powered interview session database model with comprehensive assessment tracking.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.ai_interview_interaction import AIInterviewInteraction


class InterviewType(str, enum.Enum):
    """Enum for interview types."""
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    CASE = "case"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    GENERAL = "general"


class SessionStatus(str, enum.Enum):
    """Enum for session status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AIInterviewSession(Base):
    """
    AI-powered interview session model with comprehensive assessment tracking.
    Supports real-time audio/video analysis and multi-dimensional scoring.
    """

    __tablename__ = "ai_interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Session Configuration
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType),
        nullable=False,
        default=InterviewType.GENERAL
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus),
        nullable=False,
        default=SessionStatus.ACTIVE
    )

    # Interview Context
    role_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Target role
    company_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Target company
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # easy, medium, hard
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audio/Video Analysis
    audio_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    livekit_room_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Multi-dimensional Scoring System
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Communication Scores
    verbal_communication_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pace_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Content Scores
    technical_accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    problem_solving_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    structure_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Behavioral Scores
    star_method_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For behavioral interviews
    leadership_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    teamwork_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Non-verbal Analysis (from video)
    eye_contact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_language_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Detailed Assessment Results
    strengths: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of strengths with details
    weaknesses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of weaknesses with details
    improvements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of actionable improvements
    detailed_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Question Analysis
    questions_asked: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of questions
    questions_answered: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_response_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in seconds

    # Follow-up & Recommendations
    recommended_topics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Topics to study
    recommended_practice: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Practice recommendations
    next_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Next steps for improvement

    # LangSmith Tracking
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    langsmith_trace_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_sessions")
    interactions: Mapped[list["AIInterviewInteraction"]] = relationship(
        "AIInterviewInteraction",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AIInterviewInteraction.created_at"
    )

    def __repr__(self) -> str:
        return f"<AIInterviewSession(id={self.id}, user_id={self.user_id}, type={self.interview_type}, status={self.status})>"

    def calculate_overall_score(self) -> float:
        """Calculate overall score from individual dimension scores."""
        scores = []

        # Communication scores (weight: 30%)
        comm_scores = [
            self.verbal_communication_score,
            self.clarity_score,
            self.confidence_score,
            self.pace_score
        ]
        comm_avg = sum(s for s in comm_scores if s is not None) / len([s for s in comm_scores if s is not None]) if any(s is not None for s in comm_scores) else 0
        if comm_avg > 0:
            scores.append(('communication', comm_avg, 0.30))

        # Content scores (weight: 40%)
        content_scores = [
            self.technical_accuracy_score,
            self.problem_solving_score,
            self.structure_score,
            self.relevance_score
        ]
        content_avg = sum(s for s in content_scores if s is not None) / len([s for s in content_scores if s is not None]) if any(s is not None for s in content_scores) else 0
        if content_avg > 0:
            scores.append(('content', content_avg, 0.40))

        # Behavioral scores (weight: 20%)
        behavioral_scores = [
            self.star_method_score,
            self.leadership_score,
            self.teamwork_score
        ]
        behavioral_avg = sum(s for s in behavioral_scores if s is not None) / len([s for s in behavioral_scores if s is not None]) if any(s is not None for s in behavioral_scores) else 0
        if behavioral_avg > 0:
            scores.append(('behavioral', behavioral_avg, 0.20))

        # Non-verbal scores (weight: 10%)
        nonverbal_scores = [
            self.eye_contact_score,
            self.body_language_score,
            self.engagement_score
        ]
        nonverbal_avg = sum(s for s in nonverbal_scores if s is not None) / len([s for s in nonverbal_scores if s is not None]) if any(s is not None for s in nonverbal_scores) else 0
        if nonverbal_avg > 0:
            scores.append(('nonverbal', nonverbal_avg, 0.10))

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(weight for _, _, weight in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
