"""
User profile database model for RAG context.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    """User profile model for storing context used in RAG system."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Professional Information
    current_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_companies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of companies

    # Skills & Expertise
    technical_skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of skills
    soft_skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of soft skills
    industries: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of industries

    # Education
    education: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Education history
    certifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Certifications

    # Interview Preferences
    interview_types: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # behavioral, technical, case, etc.
    difficulty_preference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # easy, medium, hard
    focus_areas: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Areas to focus on

    # Resume & Additional Context
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Flexible field

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, target_role={self.target_role})>"

    def to_context_string(self) -> str:
        """Convert profile to a natural language context string for RAG."""
        context_parts = []

        if self.current_role and self.current_company:
            context_parts.append(f"Currently working as {self.current_role} at {self.current_company}")
        elif self.current_role:
            context_parts.append(f"Currently working as {self.current_role}")

        if self.years_of_experience:
            context_parts.append(f"with {self.years_of_experience} years of experience")

        if self.target_role:
            context_parts.append(f"Preparing for {self.target_role} interviews")

        if self.technical_skills:
            skills = ", ".join(self.technical_skills.get("skills", []))
            if skills:
                context_parts.append(f"Technical skills: {skills}")

        if self.focus_areas:
            areas = ", ".join(self.focus_areas.get("areas", []))
            if areas:
                context_parts.append(f"Focus areas: {areas}")

        if self.bio:
            context_parts.append(f"Background: {self.bio}")

        return ". ".join(context_parts) + "." if context_parts else ""
