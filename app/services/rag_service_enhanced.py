"""
Enhanced RAG (Retrieval-Augmented Generation) service with comprehensive logging and monitoring.
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
from app.core.monitoring import (
    track_time,
    log_step,
    log_metric,
    log_function_call,
    log_error,
    log_warning
)
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.session import InterviewSession

logger = get_logger(__name__)


class RAGService:
    """Service for RAG-based user context retrieval with comprehensive monitoring."""

    def __init__(self):
        """Initialize RAG service with vector store and embeddings."""
        logger.info("=" * 80)
        logger.info("INITIALIZING RAG SERVICE")
        logger.info("=" * 80)

        log_step("RAG Service Init Start", {
            "embedding_model": settings.EMBEDDING_MODEL,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
            "chunk_size": 500,
            "chunk_overlap": 50
        })

        try:
            # Initialize embeddings
            with track_time("initialize_embeddings", {
                "model": settings.EMBEDDING_MODEL
            }):
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                log_step("Embeddings Initialized", {
                    "model": settings.EMBEDDING_MODEL,
                    "status": "success"
                })

            # Initialize vector store
            persist_directory = settings.CHROMA_PERSIST_DIR
            os.makedirs(persist_directory, exist_ok=True)

            with track_time("initialize_vector_store", {
                "persist_dir": persist_directory
            }):
                self.vector_store = Chroma(
                    collection_name="user_contexts",
                    embedding_function=self.embeddings,
                    persist_directory=persist_directory
                )
                log_step("Vector Store Initialized", {
                    "collection": "user_contexts",
                    "persist_directory": persist_directory,
                    "status": "success"
                })

            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

            # Set Sentry context
            set_context("rag_service", {
                "embedding_model": settings.EMBEDDING_MODEL,
                "vector_store": "ChromaDB",
                "chunk_size": 500,
                "chunk_overlap": 50,
                "persist_directory": persist_directory
            })

            logger.info("RAG Service initialized successfully")
            log_metric("rag_service_init", 1, {"status": "success"})

        except Exception as e:
            log_error(e, "rag_service_init", extra_data={
                "embedding_model": settings.EMBEDDING_MODEL,
                "persist_dir": settings.CHROMA_PERSIST_DIR
            })
            raise

    @log_function_call(level="info", log_args=True, log_result=True, track_performance=True)
    async def index_user_context(self, db: AsyncSession, user_id: int) -> bool:
        """
        Index user context into vector store for RAG retrieval.

        Args:
            db: Database session
            user_id: User ID to index

        Returns:
            True if indexing successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info(f"INDEXING USER CONTEXT - User ID: {user_id}")
        logger.info("=" * 80)

        log_step("Start Indexing", {"user_id": user_id})

        try:
            with start_span("rag.index_user", f"Index user {user_id}"):
                documents_indexed = 0

                # Step 1: Fetch user data
                with track_time("fetch_user_data", {"user_id": user_id}):
                    user_result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    user = user_result.scalar_one_or_none()

                if not user:
                    log_warning(
                        f"User {user_id} not found",
                        "index_user_context",
                        {"user_id": user_id}
                    )
                    log_metric("rag_index_failed", 1, {
                        "reason": "user_not_found",
                        "user_id": str(user_id)
                    })
                    return False

                log_step("User Data Fetched", {
                    "user_id": user_id,
                    "email": user.email,
                    "created_at": str(user.created_at)
                })

                # Step 2: Fetch user profile
                with track_time("fetch_user_profile", {"user_id": user_id}):
                    profile_result = await db.execute(
                        select(UserProfile).where(UserProfile.user_id == user_id)
                    )
                    profile = profile_result.scalar_one_or_none()

                # Step 3: Fetch user's interview history
                with track_time("fetch_interview_history", {"user_id": user_id}):
                    sessions_result = await db.execute(
                        select(InterviewSession)
                        .where(InterviewSession.user_id == user_id)
                        .order_by(InterviewSession.created_at.desc())
                        .limit(10)
                    )
                    sessions = sessions_result.scalars().all()

                log_step("Database Fetch Complete", {
                    "user_id": user_id,
                    "has_profile": profile is not None,
                    "session_count": len(sessions)
                })

                # Step 4: Build context documents
                documents = []

                # Basic user info
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
                log_step("Basic Info Document Created", {
                    "user_id": user_id,
                    "length": len(basic_info)
                })

                # Profile context
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
                        log_step("Profile Document Created", {
                            "user_id": user_id,
                            "length": len(profile_context)
                        })

                    # Resume chunks
                    if profile.resume_text:
                        with track_time("chunk_resume", {
                            "user_id": user_id,
                            "resume_length": len(profile.resume_text)
                        }):
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
                            log_step("Resume Chunked", {
                                "user_id": user_id,
                                "chunk_count": len(resume_chunks)
                            })

                # Interview history
                for idx, session in enumerate(sessions):
                    session_summary = self._build_session_summary(session)
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

                log_step("All Documents Prepared", {
                    "user_id": user_id,
                    "total_documents": len(documents)
                })

                # Step 5: Delete existing documents
                with track_time("delete_existing_docs", {"user_id": user_id}):
                    try:
                        self.vector_store.delete(where={"user_id": user_id})
                        log_step("Existing Documents Deleted", {
                            "user_id": user_id
                        })
                    except Exception as e:
                        log_warning(
                            f"Could not delete existing documents: {str(e)}",
                            "delete_vector_docs",
                            {"user_id": user_id}
                        )

                # Step 6: Add documents to vector store
                if documents:
                    with track_time("add_to_vector_store", {
                        "user_id": user_id,
                        "document_count": len(documents)
                    }):
                        self.vector_store.add_documents(documents)
                        documents_indexed = len(documents)

                    log_step("Documents Indexed Successfully", {
                        "user_id": user_id,
                        "documents_indexed": documents_indexed
                    })

                    log_metric("rag_documents_indexed", documents_indexed, {
                        "user_id": str(user_id),
                        "status": "success"
                    })

                    logger.info(
                        f"Successfully indexed {documents_indexed} documents for user {user_id}",
                        extra={
                            "user_id": user_id,
                            "documents_indexed": documents_indexed,
                            "operation": "index_user_context",
                            "status": "success"
                        }
                    )
                    return True
                else:
                    log_warning(
                        "No documents to index",
                        "index_user_context",
                        {"user_id": user_id}
                    )
                    log_metric("rag_index_empty", 1, {"user_id": str(user_id)})
                    return False

        except Exception as e:
            log_error(e, "index_user_context", user_id=user_id, extra_data={
                "documents_indexed": documents_indexed
            })
            log_metric("rag_index_error", 1, {
                "user_id": str(user_id),
                "error_type": e.__class__.__name__
            })
            return False

    def _build_session_summary(self, session: InterviewSession) -> str:
        """Build summary from interview session."""
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

        return session_summary

    @log_function_call(level="info", log_args=True, track_performance=True)
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
        logger.info("=" * 80)
        logger.info(f"RETRIEVING USER CONTEXT - User ID: {user_id}")
        logger.info("=" * 80)

        log_step("Start Retrieval", {
            "user_id": user_id,
            "query": query or "default",
            "k": k
        })

        try:
            with start_span("rag.retrieve", f"Retrieve context for user {user_id}"):
                with track_time("vector_search", {
                    "user_id": user_id,
                    "query": query or "default",
                    "k": k
                }):
                    if query:
                        results = self.vector_store.similarity_search(
                            query,
                            k=k,
                            filter={"user_id": user_id}
                        )
                    else:
                        results = self.vector_store.similarity_search(
                            "user profile interview history",
                            k=k,
                            filter={"user_id": user_id}
                        )

                context_docs = []
                for idx, doc in enumerate(results):
                    context_docs.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "type": doc.metadata.get("type", "unknown")
                    })

                log_step("Retrieval Complete", {
                    "user_id": user_id,
                    "documents_retrieved": len(context_docs),
                    "query": query or "default"
                })

                log_metric("rag_documents_retrieved", len(context_docs), {
                    "user_id": str(user_id),
                    "query_type": "custom" if query else "default"
                })

                logger.info(
                    f"Retrieved {len(context_docs)} context documents for user {user_id}",
                    extra={
                        "user_id": user_id,
                        "documents_retrieved": len(context_docs),
                        "query": query,
                        "k": k,
                        "operation": "retrieve_user_context",
                        "status": "success"
                    }
                )

                return context_docs

        except Exception as e:
            log_error(e, "retrieve_user_context", user_id=user_id, extra_data={
                "query": query,
                "k": k
            })
            log_metric("rag_retrieval_error", 1, {
                "user_id": str(user_id),
                "error_type": e.__class__.__name__
            })
            return []

    @log_function_call(level="info", track_performance=True)
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
            interview_type: Type of interview

        Returns:
            Personalized system prompt
        """
        logger.info("=" * 80)
        logger.info(f"BUILDING PERSONALIZED PROMPT - User ID: {user_id}, Type: {interview_type}")
        logger.info("=" * 80)

        log_step("Start Prompt Building", {
            "user_id": user_id,
            "interview_type": interview_type
        })

        try:
            with start_span("rag.build_prompt", f"Build prompt for user {user_id}"):
                # Retrieve context
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

                log_step("Prompt Built Successfully", {
                    "user_id": user_id,
                    "interview_type": interview_type,
                    "context_length": len(user_context),
                    "prompt_length": len(prompt),
                    "context_docs_used": len(context_docs)
                })

                log_metric("rag_prompt_built", 1, {
                    "user_id": str(user_id),
                    "interview_type": interview_type,
                    "context_docs": str(len(context_docs))
                })

                logger.info(
                    f"Built personalized prompt for user {user_id}",
                    extra={
                        "user_id": user_id,
                        "interview_type": interview_type,
                        "context_length": len(user_context),
                        "prompt_length": len(prompt),
                        "context_docs_count": len(context_docs),
                        "operation": "build_personalized_prompt",
                        "status": "success"
                    }
                )

                return prompt

        except Exception as e:
            log_error(e, "build_personalized_prompt", user_id=user_id, extra_data={
                "interview_type": interview_type
            })

            # Return fallback prompt
            fallback_prompt = f"""You are an experienced interview coach conducting a {interview_type} interview.
Introduce yourself and begin asking relevant interview questions."""

            log_warning(
                "Using fallback prompt due to error",
                "build_personalized_prompt",
                {
                    "user_id": user_id,
                    "interview_type": interview_type
                }
            )

            return fallback_prompt

    @log_function_call(level="debug", track_performance=True)
    async def get_user_summary(self, db: AsyncSession, user_id: int) -> str:
        """
        Get a concise summary of user for quick reference.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User summary string
        """
        log_step("Get User Summary", {"user_id": user_id})

        try:
            context_docs = await self.retrieve_user_context(user_id=user_id, k=3)

            if not context_docs:
                return "New candidate with no previous interview history."

            profile_info = next((doc["content"] for doc in context_docs if doc["type"] == "profile"), "")
            basic_info = next((doc["content"] for doc in context_docs if doc["type"] == "basic_info"), "")

            summary_parts = []
            if basic_info:
                summary_parts.append(basic_info)
            if profile_info:
                summary_parts.append(profile_info)

            summary = "\n".join(summary_parts) if summary_parts else "Limited candidate information available."

            log_metric("rag_summary_generated", 1, {
                "user_id": str(user_id),
                "summary_length": str(len(summary))
            })

            return summary

        except Exception as e:
            log_error(e, "get_user_summary", user_id=user_id)
            return "Error retrieving candidate information."
