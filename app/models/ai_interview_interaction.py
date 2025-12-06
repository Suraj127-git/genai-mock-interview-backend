"""
AI interview interaction model for storing conversation history.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_interview_session import AIInterviewSession


class MessageRole(str, enum.Enum):
    """Enum for message roles."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    TOOL = "tool"


class AIInterviewInteraction(Base):
    """
    Model for storing individual interactions within an AI interview session.
    Used for maintaining conversation context and analysis.
    """

    __tablename__ = "ai_interview_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ai_interview_sessions.id"), nullable=False, index=True)

    # Message Details
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Time to respond

    # Audio Analysis (if applicable)
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    audio_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transcript_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Speech Analysis Metrics
    words_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    filler_word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pause_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Tool Calls (for LangGraph)
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Tool invocations
    tool_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Tool outputs

    # Analysis Metadata
    analyzed: Mapped[bool] = mapped_column(default=False, nullable=False)
    analysis_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    session: Mapped["AIInterviewSession"] = relationship("AIInterviewSession", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<AIInterviewInteraction(id={self.id}, session_id={self.session_id}, role={self.role})>"
