"""
AI-powered interview API endpoints.
Handles AI interview sessions, user profiles, and real-time interactions.
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.ai_interview_session import AIInterviewSession, SessionStatus, InterviewType
from app.models.ai_interview_interaction import AIInterviewInteraction, MessageRole
from app.schemas.ai_interview import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    AIInterviewSessionCreate,
    AIInterviewSessionResponse,
    AIInterviewSessionDetailResponse,
    AIInterviewMessageSend,
    AIInterviewStartResponse,
    AIInterviewMessageResponse,
    AIInterviewAssessmentResponse,
    RAGIndexResponse,
    LiveKitTokenResponse
)
from app.services.rag_service import RAGService
from app.services.langgraph_interview_service import LangGraphInterviewService
from app.services.assessment_service import AssessmentService
from app.services.third_party_tools import generate_livekit_token, create_livekit_room
from app.core.logging import get_logger
from app.core.sentry import capture_exception

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
rag_service = RAGService()
interview_service = LangGraphInterviewService()
assessment_service = AssessmentService()


# User Profile Endpoints
@router.post("/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_user_profile(
    profile_data: UserProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update user profile for personalized interviews.
    """
    try:
        # Check if profile exists
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists. Use PUT /profile to update."
            )

        # Create profile
        profile = UserProfile(
            user_id=current_user.id,
            current_role=profile_data.current_role,
            current_company=profile_data.current_company,
            years_of_experience=profile_data.years_of_experience,
            target_role=profile_data.target_role,
            target_companies={"companies": profile_data.target_companies or []},
            technical_skills={"skills": profile_data.technical_skills or []},
            soft_skills={"skills": profile_data.soft_skills or []},
            industries={"industries": profile_data.industries or []},
            education={"education": profile_data.education or []},
            certifications={"certifications": profile_data.certifications or []},
            interview_types={"types": profile_data.interview_types or []},
            difficulty_preference=profile_data.difficulty_preference,
            focus_areas={"areas": profile_data.focus_areas or []},
            resume_text=profile_data.resume_text,
            bio=profile_data.bio
        )

        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        # Index profile in RAG system
        await rag_service.index_user_context(db, current_user.id)

        logger.info(f"Created profile for user {current_user.id}")
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating profile: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating profile"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile.
    """
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile.
    """
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Use POST /profile to create."
            )

        # Update fields
        update_data = profile_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field in ["target_companies", "technical_skills", "soft_skills", "industries", "interview_types", "focus_areas"]:
                setattr(profile, field, {field.rstrip('s'): value} if value else None)
            elif field in ["education", "certifications"]:
                setattr(profile, field, {field: value} if value else None)
            else:
                setattr(profile, field, value)

        await db.commit()
        await db.refresh(profile)

        # Re-index in RAG system
        await rag_service.index_user_context(db, current_user.id)

        logger.info(f"Updated profile for user {current_user.id}")
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile"
        )


@router.post("/profile/index", response_model=RAGIndexResponse)
async def index_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger RAG indexing for user profile and interview history.
    """
    try:
        success = await rag_service.index_user_context(db, current_user.id)

        return {
            "success": success,
            "user_id": current_user.id,
            "documents_indexed": 0,  # Would need to track this
            "message": "Successfully indexed user context" if success else "Indexing failed"
        }

    except Exception as e:
        logger.error(f"Error indexing profile: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error indexing profile"
        )


# AI Interview Session Endpoints
@router.post("/sessions", response_model=AIInterviewStartResponse, status_code=status.HTTP_201_CREATED)
async def start_ai_interview(
    session_data: AIInterviewSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new AI-powered interview session.
    """
    try:
        # Create session
        session = AIInterviewSession(
            user_id=current_user.id,
            title=session_data.title,
            interview_type=session_data.interview_type,
            role_context=session_data.role_context,
            company_context=session_data.company_context,
            difficulty_level=session_data.difficulty_level,
            custom_instructions=session_data.custom_instructions,
            status=SessionStatus.ACTIVE,
            started_at=datetime.utcnow()
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Start interview with LangGraph
        result = await interview_service.start_interview(
            user_id=current_user.id,
            session_id=session.id,
            interview_type=session_data.interview_type,
            initial_message=None
        )

        # Save first interaction
        if result["success"]:
            interaction = AIInterviewInteraction(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=result["response"],
                timestamp=datetime.utcnow()
            )
            db.add(interaction)
            await db.commit()

        logger.info(f"Started AI interview session {session.id} for user {current_user.id}")

        return {
            "session_id": session.id,
            "message": "Interview started successfully",
            "response": result["response"],
            "status": result["session_status"],
            "question_count": result["question_count"]
        }

    except Exception as e:
        logger.error(f"Error starting interview: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting interview session"
        )


@router.post("/sessions/{session_id}/message", response_model=AIInterviewMessageResponse)
async def send_interview_message(
    session_id: int,
    message_data: AIInterviewMessageSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message in an ongoing AI interview session.
    """
    try:
        # Verify session exists and belongs to user
        result = await db.execute(
            select(AIInterviewSession).where(
                AIInterviewSession.id == session_id,
                AIInterviewSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is {session.status}, not active"
            )

        # Save user message
        user_interaction = AIInterviewInteraction(
            session_id=session_id,
            role=MessageRole.USER,
            content=message_data.message,
            timestamp=datetime.utcnow(),
            audio_s3_key=message_data.audio_s3_key,
            audio_duration_seconds=message_data.audio_duration_seconds
        )
        db.add(user_interaction)
        await db.commit()

        # Continue interview (simplified - would need to pass actual state)
        # For now, create a mock response
        response_text = "Thank you for your response. Let me ask you another question..."

        # Save AI response
        ai_interaction = AIInterviewInteraction(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            timestamp=datetime.utcnow()
        )
        db.add(ai_interaction)
        await db.commit()

        return {
            "session_id": session_id,
            "response": response_text,
            "status": session.status.value,
            "question_count": 1,  # Would track this properly
            "analysis": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing message"
        )


@router.post("/sessions/{session_id}/complete", response_model=AIInterviewSessionResponse)
async def complete_ai_interview(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete an AI interview session and generate assessment.
    """
    try:
        # Verify session
        result = await db.execute(
            select(AIInterviewSession).where(
                AIInterviewSession.id == session_id,
                AIInterviewSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Update session status
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()

        # Calculate duration
        if session.started_at:
            duration = (session.completed_at - session.started_at).total_seconds()
            session.duration_seconds = int(duration)

        await db.commit()

        # Generate comprehensive assessment
        await assessment_service.assess_interview_session(db, session_id)

        await db.refresh(session)

        logger.info(f"Completed AI interview session {session_id}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing interview: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error completing interview"
        )


@router.get("/sessions", response_model=List[AIInterviewSessionResponse])
async def list_ai_interview_sessions(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all AI interview sessions for current user.
    """
    try:
        result = await db.execute(
            select(AIInterviewSession)
            .where(AIInterviewSession.user_id == current_user.id)
            .order_by(desc(AIInterviewSession.created_at))
            .offset(skip)
            .limit(limit)
        )
        sessions = result.scalars().all()

        return sessions

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing sessions"
        )


@router.get("/sessions/{session_id}", response_model=AIInterviewSessionDetailResponse)
async def get_ai_interview_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed AI interview session with interactions.
    """
    try:
        result = await db.execute(
            select(AIInterviewSession).where(
                AIInterviewSession.id == session_id,
                AIInterviewSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Fetch interactions
        interactions_result = await db.execute(
            select(AIInterviewInteraction)
            .where(AIInterviewInteraction.session_id == session_id)
            .order_by(AIInterviewInteraction.created_at)
        )
        interactions = interactions_result.scalars().all()

        # Build response
        response_data = {
            **session.__dict__,
            "interactions": interactions
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching session"
        )


@router.post("/sessions/{session_id}/assess", response_model=AIInterviewAssessmentResponse)
async def assess_interview_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate or re-generate assessment for an interview session.
    """
    try:
        # Verify session
        result = await db.execute(
            select(AIInterviewSession).where(
                AIInterviewSession.id == session_id,
                AIInterviewSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Generate assessment
        assessment = await assessment_service.assess_interview_session(db, session_id)

        return {
            "session_id": session_id,
            **assessment
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing session: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating assessment"
        )


# LiveKit Integration
@router.post("/livekit/token", response_model=LiveKitTokenResponse)
async def get_livekit_token(
    room_name: str,
    participant_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Generate LiveKit token for real-time audio/video.
    """
    try:
        participant = participant_name or current_user.name or current_user.email

        result = await generate_livekit_token(
            room_name=room_name,
            participant_name=participant
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LiveKit service unavailable"
            )

        return {
            "token": result["token"],
            "room_name": result["room_name"],
            "participant_name": result["participant_name"],
            "url": result.get("url", ""),
            "expires_at": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating LiveKit token: {e}", exc_info=True)
        capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating LiveKit token"
        )
