"""
LangGraph-based AI interview service with multi-agent workflow orchestration.
Integrates with third-party services via tool calling.
"""
from typing import Annotated, Dict, List, Optional, TypedDict, Sequence
from datetime import datetime
import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langsmith import Client as LangSmithClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.services.rag_service import RAGService

logger = get_logger(__name__)


# Define the agent state
class InterviewState(TypedDict):
    """State schema for the interview agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: int
    session_id: int
    interview_type: str
    user_context: str
    current_question_count: int
    max_questions: int
    session_status: str
    analysis_results: Dict


class LangGraphInterviewService:
    """
    LangGraph-based interview service with workflow orchestration.
    Manages AI-powered interviews with real-time analysis and tool calling.
    """

    def __init__(self):
        """Initialize LangGraph interview service."""
        self.rag_service = RAGService()

        # Initialize LLM (Groq for fast responses)
        if settings.GROQ_API_KEY:
            self.llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL,
                temperature=0.7,
                max_tokens=1024
            )
        else:
            # Fallback to OpenAI
            self.llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                temperature=0.7,
                max_tokens=1024
            )

        # Initialize LangSmith client for observability
        self.langsmith_client = None
        if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
            try:
                self.langsmith_client = LangSmithClient(api_key=settings.LANGCHAIN_API_KEY)
                logger.info("LangSmith tracing enabled")
            except Exception as e:
                logger.warning(f"Could not initialize LangSmith: {e}")

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow for interview orchestration.

        Returns:
            Compiled StateGraph workflow
        """
        # Create the graph
        workflow = StateGraph(InterviewState)

        # Define nodes
        workflow.add_node("prepare_context", self._prepare_context_node)
        workflow.add_node("conduct_interview", self._conduct_interview_node)
        workflow.add_node("analyze_response", self._analyze_response_node)
        workflow.add_node("generate_feedback", self._generate_feedback_node)
        workflow.add_node("check_completion", self._check_completion_node)

        # Define edges
        workflow.set_entry_point("prepare_context")
        workflow.add_edge("prepare_context", "conduct_interview")
        workflow.add_edge("conduct_interview", "analyze_response")
        workflow.add_edge("analyze_response", "check_completion")

        # Conditional edge: continue or end
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "conduct_interview",
                "end": "generate_feedback"
            }
        )

        workflow.add_edge("generate_feedback", END)

        return workflow.compile()

    async def _prepare_context_node(self, state: InterviewState) -> InterviewState:
        """
        Prepare user context using RAG.

        Args:
            state: Current interview state

        Returns:
            Updated state with user context
        """
        logger.info(f"Preparing context for user {state['user_id']}")

        try:
            # This would need database session - simplified for now
            user_context = f"User ID: {state['user_id']}, Interview Type: {state['interview_type']}"
            state["user_context"] = user_context
            state["current_question_count"] = 0
            state["max_questions"] = 5
            state["session_status"] = "active"
            state["analysis_results"] = {}

        except Exception as e:
            logger.error(f"Error preparing context: {e}")
            state["user_context"] = "Error loading user context"

        return state

    async def _conduct_interview_node(self, state: InterviewState) -> InterviewState:
        """
        Conduct interview by generating questions and processing responses.

        Args:
            state: Current interview state

        Returns:
            Updated state with new messages
        """
        logger.info(f"Conducting interview - Question {state['current_question_count']}")

        # Build system message with user context
        system_message = SystemMessage(
            content=f"""You are an expert interview coach conducting a {state['interview_type']} interview.

User Context:
{state['user_context']}

Your task is to ask relevant interview questions, provide constructive feedback, and help the candidate improve.
You've asked {state['current_question_count']} of {state['max_questions']} questions so far."""
        )

        # Prepare messages for LLM
        messages = [system_message] + list(state["messages"])

        try:
            # Get LLM response
            response = await self.llm.ainvoke(messages)
            state["messages"].append(response)

        except Exception as e:
            logger.error(f"Error in interview node: {e}")
            error_message = AIMessage(content="I apologize, but I encountered an error. Let's continue.")
            state["messages"].append(error_message)

        return state

    async def _analyze_response_node(self, state: InterviewState) -> InterviewState:
        """
        Analyze user's response for real-time feedback.

        Args:
            state: Current interview state

        Returns:
            Updated state with analysis results
        """
        logger.info("Analyzing user response")

        # Get last user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]

        if not user_messages:
            return state

        last_response = user_messages[-1].content

        # Simple analysis (can be enhanced with more sophisticated NLP)
        analysis = {
            "response_length": len(last_response),
            "word_count": len(last_response.split()),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store analysis
        question_num = state["current_question_count"]
        state["analysis_results"][f"question_{question_num}"] = analysis

        return state

    async def _check_completion_node(self, state: InterviewState) -> InterviewState:
        """
        Check if interview should continue or end.

        Args:
            state: Current interview state

        Returns:
            Updated state
        """
        state["current_question_count"] += 1

        if state["current_question_count"] >= state["max_questions"]:
            state["session_status"] = "completed"

        return state

    def _should_continue(self, state: InterviewState) -> str:
        """
        Determine if interview should continue.

        Args:
            state: Current interview state

        Returns:
            "continue" or "end"
        """
        if state["session_status"] == "completed":
            return "end"
        return "continue"

    async def _generate_feedback_node(self, state: InterviewState) -> InterviewState:
        """
        Generate comprehensive feedback at the end of interview.

        Args:
            state: Current interview state

        Returns:
            Updated state with feedback
        """
        logger.info("Generating comprehensive feedback")

        feedback_prompt = f"""Based on the interview conversation above, provide comprehensive feedback.

Interview Type: {state['interview_type']}
Questions Asked: {state['current_question_count']}

Provide:
1. Overall assessment
2. Key strengths demonstrated
3. Areas for improvement
4. Specific recommendations

Format as JSON with keys: overall_assessment, strengths (array), improvements (array), recommendations (array)"""

        try:
            messages = list(state["messages"]) + [HumanMessage(content=feedback_prompt)]
            response = await self.llm.ainvoke(messages)
            state["messages"].append(response)

        except Exception as e:
            logger.error(f"Error generating feedback: {e}")

        return state

    async def start_interview(
        self,
        user_id: int,
        session_id: int,
        interview_type: str,
        initial_message: Optional[str] = None
    ) -> Dict:
        """
        Start a new AI-powered interview session.

        Args:
            user_id: User ID
            session_id: Session ID
            interview_type: Type of interview
            initial_message: Optional initial message from user

        Returns:
            Interview response
        """
        logger.info(f"Starting interview for user {user_id}, session {session_id}")

        # Initialize state
        initial_state: InterviewState = {
            "messages": [],
            "user_id": user_id,
            "session_id": session_id,
            "interview_type": interview_type,
            "user_context": "",
            "current_question_count": 0,
            "max_questions": 5,
            "session_status": "initializing",
            "analysis_results": {}
        }

        if initial_message:
            initial_state["messages"].append(HumanMessage(content=initial_message))

        try:
            # Run workflow (just preparation and first question)
            result = await self.workflow.ainvoke(initial_state)

            # Extract AI response
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            response_text = ai_messages[-1].content if ai_messages else "Hello! Let's begin the interview."

            return {
                "response": response_text,
                "session_status": result["session_status"],
                "question_count": result["current_question_count"],
                "success": True
            }

        except Exception as e:
            logger.error(f"Error starting interview: {e}", exc_info=True)
            return {
                "response": "I apologize, but I encountered an error starting the interview. Please try again.",
                "session_status": "error",
                "success": False,
                "error": str(e)
            }

    async def continue_interview(
        self,
        session_id: int,
        user_message: str,
        current_state: InterviewState
    ) -> Dict:
        """
        Continue an ongoing interview session.

        Args:
            session_id: Session ID
            user_message: User's message/response
            current_state: Current interview state

        Returns:
            Interview response
        """
        logger.info(f"Continuing interview for session {session_id}")

        try:
            # Add user message to state
            current_state["messages"].append(HumanMessage(content=user_message))

            # Run workflow
            result = await self.workflow.ainvoke(current_state)

            # Extract AI response
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            response_text = ai_messages[-1].content if ai_messages else "Please continue."

            return {
                "response": response_text,
                "session_status": result["session_status"],
                "question_count": result["current_question_count"],
                "analysis": result["analysis_results"],
                "success": True
            }

        except Exception as e:
            logger.error(f"Error continuing interview: {e}", exc_info=True)
            return {
                "response": "I apologize for the interruption. Please continue.",
                "session_status": current_state["session_status"],
                "success": False,
                "error": str(e)
            }
