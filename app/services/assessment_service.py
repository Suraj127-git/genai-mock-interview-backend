"""
Comprehensive assessment and scoring service for AI interviews.
Analyzes interviews across multiple dimensions with AI-powered evaluation.
"""
from typing import Dict, List, Optional
from datetime import datetime
import re

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai_interview_session import AIInterviewSession
from app.models.ai_interview_interaction import AIInterviewInteraction, MessageRole

logger = get_logger(__name__)


class AssessmentService:
    """
    Service for comprehensive interview assessment and scoring.
    """

    def __init__(self):
        """Initialize assessment service with LLM."""
        # Use Groq for fast assessments
        if settings.GROQ_API_KEY:
            self.llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL,
                temperature=0.3  # Lower temperature for more consistent scoring
            )
        else:
            self.llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                temperature=0.3
            )

    async def assess_interview_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict:
        """
        Perform comprehensive assessment of an interview session.

        Args:
            db: Database session
            session_id: Interview session ID

        Returns:
            Assessment results with scores and feedback
        """
        logger.info(f"Assessing interview session {session_id}")

        try:
            # Fetch session
            result = await db.execute(
                select(AIInterviewSession).where(AIInterviewSession.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Fetch interactions
            interactions_result = await db.execute(
                select(AIInterviewInteraction)
                .where(AIInterviewInteraction.session_id == session_id)
                .order_by(AIInterviewInteraction.created_at)
            )
            interactions = interactions_result.scalars().all()

            # Build conversation transcript
            transcript = self._build_transcript(interactions)

            # Perform multi-dimensional assessment
            communication_scores = await self._assess_communication(transcript, interactions)
            content_scores = await self._assess_content(transcript, session.interview_type)
            behavioral_scores = await self._assess_behavioral(transcript, session.interview_type)
            overall_feedback = await self._generate_overall_feedback(
                transcript,
                session.interview_type,
                communication_scores,
                content_scores,
                behavioral_scores
            )

            # Calculate overall score
            overall_score = self._calculate_overall_score(
                communication_scores,
                content_scores,
                behavioral_scores
            )

            # Compile assessment results
            assessment = {
                "overall_score": overall_score,
                "communication_scores": communication_scores,
                "content_scores": content_scores,
                "behavioral_scores": behavioral_scores,
                "feedback": overall_feedback,
                "assessed_at": datetime.utcnow().isoformat()
            }

            # Update session with assessment results
            await self._update_session_scores(db, session, assessment)

            return assessment

        except Exception as e:
            logger.error(f"Error assessing session: {e}", exc_info=True)
            raise

    def _build_transcript(self, interactions: List[AIInterviewInteraction]) -> str:
        """Build conversation transcript from interactions."""
        lines = []

        for interaction in interactions:
            role_label = "Interviewer" if interaction.role == MessageRole.ASSISTANT else "Candidate"
            lines.append(f"{role_label}: {interaction.content}")

        return "\n\n".join(lines)

    async def _assess_communication(
        self,
        transcript: str,
        interactions: List[AIInterviewInteraction]
    ) -> Dict:
        """
        Assess communication skills.

        Returns:
            Dictionary with communication scores
        """
        # Calculate speech metrics from interactions
        candidate_interactions = [i for i in interactions if i.role == MessageRole.USER]

        total_words = 0
        total_duration = 0
        filler_words = 0

        for interaction in candidate_interactions:
            words = interaction.content.split()
            total_words += len(words)

            if interaction.audio_duration_seconds:
                total_duration += interaction.audio_duration_seconds

            # Count filler words
            filler_patterns = r'\b(um|uh|like|you know|basically|actually|literally)\b'
            filler_words += len(re.findall(filler_patterns, interaction.content.lower()))

        # Calculate WPM
        words_per_minute = (total_words / total_duration * 60) if total_duration > 0 else 150

        # LLM-based communication assessment
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert communication coach. Assess the candidate's communication skills based on the transcript.

Rate the following on a scale of 0-100:
1. Verbal clarity (how clear and articulate)
2. Confidence level (how confident they sound)
3. Pace appropriateness (too fast, too slow, or just right)

Provide scores as JSON: {"clarity": X, "confidence": Y, "pace": Z}"""),
            HumanMessage(content=f"Transcript:\n{transcript}\n\nWords per minute: {words_per_minute:.0f}\nFiller words: {filler_words}")
        ])

        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            scores = self._parse_json_response(response.content)

            return {
                "verbal_communication_score": (scores.get("clarity", 70) + scores.get("confidence", 70)) / 2,
                "clarity_score": scores.get("clarity", 70),
                "confidence_score": scores.get("confidence", 70),
                "pace_score": scores.get("pace", 70),
                "words_per_minute": words_per_minute,
                "filler_word_count": filler_words
            }

        except Exception as e:
            logger.error(f"Error in communication assessment: {e}")
            return {
                "verbal_communication_score": 70.0,
                "clarity_score": 70.0,
                "confidence_score": 70.0,
                "pace_score": 70.0,
                "words_per_minute": words_per_minute,
                "filler_word_count": filler_words
            }

    async def _assess_content(self, transcript: str, interview_type: str) -> Dict:
        """
        Assess content quality and relevance.

        Returns:
            Dictionary with content scores
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are an expert {interview_type} interviewer. Assess the candidate's responses for content quality.

Rate the following on a scale of 0-100:
1. Technical accuracy (how correct/accurate their answers are)
2. Problem-solving ability (how well they approach problems)
3. Structure (how well-organized their responses are)
4. Relevance (how relevant their answers are to questions)

Provide scores as JSON: {{"technical_accuracy": X, "problem_solving": Y, "structure": Z, "relevance": W}}"""),
            HumanMessage(content=f"Interview Type: {interview_type}\n\nTranscript:\n{transcript}")
        ])

        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            scores = self._parse_json_response(response.content)

            return {
                "technical_accuracy_score": scores.get("technical_accuracy", 70),
                "problem_solving_score": scores.get("problem_solving", 70),
                "structure_score": scores.get("structure", 70),
                "relevance_score": scores.get("relevance", 70)
            }

        except Exception as e:
            logger.error(f"Error in content assessment: {e}")
            return {
                "technical_accuracy_score": 70.0,
                "problem_solving_score": 70.0,
                "structure_score": 70.0,
                "relevance_score": 70.0
            }

    async def _assess_behavioral(self, transcript: str, interview_type: str) -> Dict:
        """
        Assess behavioral aspects (especially for behavioral interviews).

        Returns:
            Dictionary with behavioral scores
        """
        if interview_type.lower() != "behavioral":
            # Return neutral scores for non-behavioral interviews
            return {
                "star_method_score": None,
                "leadership_score": None,
                "teamwork_score": None
            }

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert behavioral interviewer. Assess the candidate's behavioral responses.

Rate the following on a scale of 0-100:
1. STAR method usage (Situation, Task, Action, Result)
2. Leadership demonstration
3. Teamwork and collaboration

Provide scores as JSON: {"star_method": X, "leadership": Y, "teamwork": Z}"""),
            HumanMessage(content=f"Transcript:\n{transcript}")
        ])

        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            scores = self._parse_json_response(response.content)

            return {
                "star_method_score": scores.get("star_method", 70),
                "leadership_score": scores.get("leadership", 70),
                "teamwork_score": scores.get("teamwork", 70)
            }

        except Exception as e:
            logger.error(f"Error in behavioral assessment: {e}")
            return {
                "star_method_score": 70.0,
                "leadership_score": 70.0,
                "teamwork_score": 70.0
            }

    async def _generate_overall_feedback(
        self,
        transcript: str,
        interview_type: str,
        communication_scores: Dict,
        content_scores: Dict,
        behavioral_scores: Dict
    ) -> Dict:
        """
        Generate comprehensive feedback with strengths, weaknesses, and recommendations.

        Returns:
            Dictionary with detailed feedback
        """
        scores_summary = f"""
Communication Scores:
- Clarity: {communication_scores.get('clarity_score', 0)}/100
- Confidence: {communication_scores.get('confidence_score', 0)}/100
- Pace: {communication_scores.get('pace_score', 0)}/100

Content Scores:
- Technical Accuracy: {content_scores.get('technical_accuracy_score', 0)}/100
- Problem Solving: {content_scores.get('problem_solving_score', 0)}/100
- Structure: {content_scores.get('structure_score', 0)}/100
- Relevance: {content_scores.get('relevance_score', 0)}/100
"""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert interview coach. Based on the interview transcript and scores, provide comprehensive feedback.

Provide:
1. Top 3-5 strengths (specific, actionable points)
2. Top 3-5 areas for improvement (specific, actionable points)
3. Detailed feedback paragraph (2-3 sentences)
4. 3-5 recommended next steps for improvement
5. 2-3 recommended topics to study

Format as JSON with keys: strengths (array of strings), improvements (array of strings), detailed_feedback (string), next_steps (array of strings), recommended_topics (array of strings)"""),
            HumanMessage(content=f"Interview Type: {interview_type}\n\nScores:\n{scores_summary}\n\nTranscript:\n{transcript}")
        ])

        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            feedback = self._parse_json_response(response.content)

            return {
                "strengths": feedback.get("strengths", []),
                "weaknesses": feedback.get("improvements", []),
                "detailed_feedback": feedback.get("detailed_feedback", ""),
                "next_steps": feedback.get("next_steps", []),
                "recommended_topics": feedback.get("recommended_topics", [])
            }

        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            return {
                "strengths": ["Completed the interview", "Engaged with questions"],
                "weaknesses": ["Could provide more specific examples"],
                "detailed_feedback": "Overall decent performance with room for improvement.",
                "next_steps": ["Practice more interview questions"],
                "recommended_topics": ["Interview techniques"]
            }

    def _calculate_overall_score(
        self,
        communication_scores: Dict,
        content_scores: Dict,
        behavioral_scores: Dict
    ) -> float:
        """Calculate weighted overall score."""
        scores = []

        # Communication (30% weight)
        comm_avg = (
            communication_scores.get("clarity_score", 0) +
            communication_scores.get("confidence_score", 0) +
            communication_scores.get("pace_score", 0)
        ) / 3
        scores.append(comm_avg * 0.30)

        # Content (50% weight)
        content_avg = (
            content_scores.get("technical_accuracy_score", 0) +
            content_scores.get("problem_solving_score", 0) +
            content_scores.get("structure_score", 0) +
            content_scores.get("relevance_score", 0)
        ) / 4
        scores.append(content_avg * 0.50)

        # Behavioral (20% weight, if applicable)
        if behavioral_scores.get("star_method_score") is not None:
            behavioral_avg = (
                behavioral_scores.get("star_method_score", 0) +
                behavioral_scores.get("leadership_score", 0) +
                behavioral_scores.get("teamwork_score", 0)
            ) / 3
            scores.append(behavioral_avg * 0.20)

        return round(sum(scores), 2)

    async def _update_session_scores(
        self,
        db: AsyncSession,
        session: AIInterviewSession,
        assessment: Dict
    ):
        """Update session with assessment results."""
        # Update scores
        session.overall_score = assessment["overall_score"]

        # Communication scores
        comm = assessment["communication_scores"]
        session.verbal_communication_score = comm.get("verbal_communication_score")
        session.clarity_score = comm.get("clarity_score")
        session.confidence_score = comm.get("confidence_score")
        session.pace_score = comm.get("pace_score")

        # Content scores
        content = assessment["content_scores"]
        session.technical_accuracy_score = content.get("technical_accuracy_score")
        session.problem_solving_score = content.get("problem_solving_score")
        session.structure_score = content.get("structure_score")
        session.relevance_score = content.get("relevance_score")

        # Behavioral scores
        behavioral = assessment["behavioral_scores"]
        session.star_method_score = behavioral.get("star_method_score")
        session.leadership_score = behavioral.get("leadership_score")
        session.teamwork_score = behavioral.get("teamwork_score")

        # Feedback
        feedback = assessment["feedback"]
        session.strengths = {"strengths": feedback.get("strengths", [])}
        session.weaknesses = {"weaknesses": feedback.get("weaknesses", [])}
        session.improvements = {"improvements": feedback.get("weaknesses", [])}
        session.detailed_feedback = feedback.get("detailed_feedback", "")
        session.recommended_topics = {"topics": feedback.get("recommended_topics", [])}
        session.next_steps = {"steps": feedback.get("next_steps", [])}

        await db.commit()
        logger.info(f"Updated session {session.id} with assessment results")

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        import json

        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return json.loads(response)

        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            return {}
