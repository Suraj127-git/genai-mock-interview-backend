"""
RAG (Retrieval-Augmented Generation) service for user context retrieval.
Uses vector embeddings to retrieve relevant user information for personalized interviews.
"""
import os
from typing import Dict, List, Optional
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.core.sentry import start_span, capture_exception, add_breadcrumb, set_context
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.session import InterviewSession

logger = get_logger(__name__)


class RAGService:
    """Service for RAG-based user context retrieval."""

    def __init__(self):
        """Initialize RAG service with vector store and embeddings."""
        logger.info("Initializing RAG service", extra={
            "embedding_model": settings.EMBEDDING_MODEL,
            "persist_dir": settings.CHROMA_PERSIST_DIR
        })

        add_breadcrumb(
            "RAG Service Initialization",
            category="rag",
            level="info",
            data={
                "embedding_model": settings.EMBEDDING_MODEL,
                "persist_directory": settings.CHROMA_PERSIST_DIR
            }
        )

        try:
            with start_span("rag.init.embeddings", "Initialize HuggingFace Embeddings"):
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                logger.info("HuggingFace embeddings initialized successfully", extra={
                    "model": settings.EMBEDDING_MODEL
                })

            # Initialize vector store
            persist_directory = settings.CHROMA_PERSIST_DIR
            os.makedirs(persist_directory, exist_ok=True)

            with start_span("rag.init.vector_store", "Initialize ChromaDB Vector Store"):
                self.vector_store = Chroma(
                    collection_name="user_contexts",
                    embedding_function=self.embeddings,
                    persist_directory=persist_directory
                )
                logger.info("ChromaDB vector store initialized successfully", extra={
                    "collection": "user_contexts",
                    "persist_directory": persist_directory
                })

            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

            set_context("rag_service", {
                "embedding_model": settings.EMBEDDING_MODEL,
                "vector_store": "ChromaDB",
                "chunk_size": 500,
                "chunk_overlap": 50
            })

            logger.info("RAG service initialization complete")

        except Exception as e:
            logger.error("Failed to initialize RAG service", exc_info=True, extra={
                "error": str(e),
                "embedding_model": settings.EMBEDDING_MODEL
            })
            capture_exception(e, tags={"service": "rag", "operation": "init"})
            raise

    async def index_user_context(self, db: AsyncSession, user_id: int) -> bool:
        """
        Index user context into vector store for RAG retrieval.

        Args:
            db: Database session
            user_id: User ID to index

        Returns:
            True if indexing successful, False otherwise
        """
        logger.info(f"Starting RAG indexing for user {user_id}", extra={
            "user_id": user_id,
            "operation": "index_user_context"
        })

        add_breadcrumb(
            "Start RAG Indexing",
            category="rag",
            level="info",
            data={"user_id": user_id}
        )

        try:
            with start_span("rag.index", f"Index user {user_id}"):
                # Fetch user data
                with start_span("rag.index.fetch_user", "Fetch user from database"):
                    user_result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    user = user_result.scalar_one_or_none()

                if not user:
                    logger.warning(f"User {user_id} not found for indexing", extra={
                        "user_id": user_id,
                        "reason": "user_not_found"
                    })
                    add_breadcrumb(
                        "User not found",
                        category="rag",
                        level="warning",
                        data={"user_id": user_id}
                    )
                    return False

                logger.debug(f"Fetched user data for {user.email}", extra={
                    "user_id": user_id,
                    "email": user.email
                })

            # Fetch user profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            # Fetch user's interview history
            sessions_result = await db.execute(
                select(InterviewSession)
                .where(InterviewSession.user_id == user_id)
                .order_by(InterviewSession.created_at.desc())
                .limit(10)  # Last 10 sessions
            )
            sessions = sessions_result.scalars().all()

            # Build context documents
            documents = []

            # 1. User basic info
            basic_info = f"User: {user.name or user.email}\nEmail: {user.email}\nAccount created: {user.created_at.strftime('%Y-%m-%d')}"
            documents.append(
                Document(
                    page_content=basic_info,
                    metadata={
                        "user_id": user_id,
                        "type": "basic_info",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            )

            # 2. User profile context
            if profile:
                profile_context = profile.to_context_string()
                if profile_context:
                    documents.append(
                        Document(
                            page_content=profile_context,
                            metadata={
                                "user_id": user_id,
                                "type": "profile",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                    )

                # Add resume if available
                if profile.resume_text:
                    resume_chunks = self.text_splitter.split_text(profile.resume_text)
                    for i, chunk in enumerate(resume_chunks):
                        documents.append(
                            Document(
                                page_content=chunk,
                                metadata={
                                    "user_id": user_id,
                                    "type": "resume",
                                    "chunk": i,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        )

            # 3. Interview history
            for session in sessions:
                session_summary = f"Interview Session: {session.title}\n"
                session_summary += f"Date: {session.created_at.strftime('%Y-%m-%d')}\n"

                if session.question:
                    session_summary += f"Question: {session.question}\n"

                if session.overall_score:
                    session_summary += f"Overall Score: {session.overall_score}/100\n"

                if session.detailed_feedback:
                    session_summary += f"Feedback: {session.detailed_feedback}\n"

                if session.strengths and isinstance(session.strengths, dict):
                    strengths = session.strengths.get('strengths', [])
                    if strengths:
                        session_summary += f"Strengths: {', '.join(strengths)}\n"

                if session.improvements and isinstance(session.improvements, dict):
                    improvements = session.improvements.get('improvements', [])
                    if improvements:
                        session_summary += f"Areas for Improvement: {', '.join(improvements)}\n"

                documents.append(
                    Document(
                        page_content=session_summary,
                        metadata={
                            "user_id": user_id,
                            "type": "session_history",
                            "session_id": session.id,
                            "timestamp": session.created_at.isoformat()
                        }
                    )
                )

            # Delete existing user documents from vector store
            try:
                self.vector_store.delete(
                    where={"user_id": user_id}
                )
            except Exception as e:
                logger.warning(f"Could not delete existing documents: {e}")

            # Add documents to vector store
            if documents:
                self.vector_store.add_documents(documents)
                logger.info(f"Indexed {len(documents)} documents for user {user_id}")
                return True
            else:
                logger.warning(f"No documents to index for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Error indexing user context: {e}", exc_info=True)
            return False

    async def retrieve_user_context(
        self,
        user_id: int,
        query: Optional[str] = None,
        k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant user context using RAG.

        Args:
            user_id: User ID to retrieve context for
            query: Optional query to search for specific context
            k: Number of documents to retrieve

        Returns:
            List of relevant context documents
        """
        try:
            if query:
                # Semantic search with query
                results = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter={"user_id": user_id}
                )
            else:
                # Get all user documents
                results = self.vector_store.similarity_search(
                    "user profile interview history",
                    k=k,
                    filter={"user_id": user_id}
                )

            context_docs = []
            for doc in results:
                context_docs.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "type": doc.metadata.get("type", "unknown")
                })

            return context_docs

        except Exception as e:
            logger.error(f"Error retrieving user context: {e}", exc_info=True)
            return []

    async def build_personalized_prompt(
        self,
        db: AsyncSession,
        user_id: int,
        interview_type: str = "general"
    ) -> str:
        """
        Build a personalized system prompt using RAG-retrieved context.

        Args:
            db: Database session
            user_id: User ID
            interview_type: Type of interview (behavioral, technical, etc.)

        Returns:
            Personalized system prompt
        """
        try:
            # Retrieve user context
            context_docs = await self.retrieve_user_context(
                user_id=user_id,
                query=f"{interview_type} interview preparation",
                k=5
            )

            # Build context string
            context_parts = []
            for doc in context_docs:
                context_parts.append(doc["content"])

            user_context = "\n\n".join(context_parts) if context_parts else "No previous context available."

            # Build personalized prompt
            prompt = f"""You are an experienced interview coach conducting a {interview_type} interview.

**Candidate Context:**
{user_context}

**Your Role:**
- Conduct a realistic {interview_type} interview
- Ask relevant questions based on the candidate's background and experience
- Provide real-time feedback and encouragement
- Adapt questions based on the candidate's responses
- Be supportive but maintain professional interview standards
- After each response, provide brief constructive feedback before moving to the next question

**Interview Guidelines:**
- Start with a personalized introduction that references the candidate's background
- Ask 3-5 relevant questions for this interview session
- Listen carefully to responses and ask follow-up questions when needed
- Provide balanced feedback highlighting both strengths and areas for improvement
- End with actionable recommendations for improvement

Begin the interview now with a warm, personalized introduction."""

            return prompt

        except Exception as e:
            logger.error(f"Error building personalized prompt: {e}", exc_info=True)
            # Return fallback prompt
            return f"""You are an experienced interview coach conducting a {interview_type} interview.
Introduce yourself and begin asking relevant interview questions."""

    async def get_user_summary(self, db: AsyncSession, user_id: int) -> str:
        """
        Get a concise summary of user for quick reference.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User summary string
        """
        try:
            context_docs = await self.retrieve_user_context(user_id=user_id, k=3)

            if not context_docs:
                return "New candidate with no previous interview history."

            # Extract key information
            profile_info = next((doc["content"] for doc in context_docs if doc["type"] == "profile"), "")
            basic_info = next((doc["content"] for doc in context_docs if doc["type"] == "basic_info"), "")

            summary_parts = []
            if basic_info:
                summary_parts.append(basic_info)
            if profile_info:
                summary_parts.append(profile_info)

            return "\n".join(summary_parts) if summary_parts else "Limited candidate information available."

        except Exception as e:
            logger.error(f"Error getting user summary: {e}", exc_info=True)
            return "Error retrieving candidate information."
