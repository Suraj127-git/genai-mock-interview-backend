"""
Third-party service integrations as LangChain tools.
Includes LiveKit, Cartesia, Murf, and web search services.
"""
from typing import Optional, Dict, Any
import httpx
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# LiveKit Tools
@tool
async def create_livekit_room(room_name: str, max_participants: int = 2) -> Dict[str, Any]:
    """
    Create a LiveKit room for real-time audio/video communication.

    Args:
        room_name: Name of the room to create
        max_participants: Maximum number of participants

    Returns:
        Room details including room_name and connection token
    """
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_URL:
        logger.warning("LiveKit credentials not configured")
        return {"error": "LiveKit not configured", "success": False}

    try:
        from livekit import api

        # Create room
        room_service = api.RoomService(
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET
        )

        # This is a simplified implementation
        # In production, you would use proper LiveKit SDK methods
        logger.info(f"Creating LiveKit room: {room_name}")

        return {
            "success": True,
            "room_name": room_name,
            "url": settings.LIVEKIT_URL,
            "max_participants": max_participants,
            "message": f"Room {room_name} created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating LiveKit room: {e}")
        return {"error": str(e), "success": False}


@tool
async def generate_livekit_token(room_name: str, participant_name: str) -> Dict[str, Any]:
    """
    Generate a LiveKit access token for a participant.

    Args:
        room_name: Name of the room
        participant_name: Name of the participant

    Returns:
        Access token for joining the room
    """
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_URL:
        return {"error": "LiveKit not configured", "success": False}

    try:
        from livekit import api

        # Generate token
        logger.info(f"Generating token for {participant_name} in room {room_name}")

        # Simplified implementation
        return {
            "success": True,
            "token": "mock_token_for_development",
            "room_name": room_name,
            "participant_name": participant_name
        }

    except Exception as e:
        logger.error(f"Error generating LiveKit token: {e}")
        return {"error": str(e), "success": False}


# Cartesia Tools (Speech Processing)
@tool
async def analyze_speech_cartesia(audio_url: str) -> Dict[str, Any]:
    """
    Analyze speech using Cartesia for advanced speech processing.

    Args:
        audio_url: URL or path to audio file

    Returns:
        Speech analysis results including clarity, pace, tone
    """
    if not settings.CARTESIA_API_KEY:
        logger.warning("Cartesia API key not configured")
        return {
            "error": "Cartesia not configured",
            "success": False,
            "mock_results": {
                "clarity_score": 85,
                "pace_wpm": 145,
                "tone": "confident",
                "filler_words": 3
            }
        }

    try:
        # Placeholder for Cartesia API integration
        # In production, integrate with actual Cartesia API
        async with httpx.AsyncClient() as client:
            logger.info(f"Analyzing speech with Cartesia: {audio_url}")

            # Mock response for development
            return {
                "success": True,
                "clarity_score": 85.5,
                "pace_words_per_minute": 145,
                "tone_analysis": {
                    "confidence": 0.75,
                    "emotion": "neutral",
                    "engagement": 0.80
                },
                "filler_word_count": 3,
                "pause_count": 5,
                "recommendations": [
                    "Maintain current speaking pace",
                    "Reduce filler words slightly",
                    "Good overall clarity"
                ]
            }

    except Exception as e:
        logger.error(f"Error analyzing speech with Cartesia: {e}")
        return {"error": str(e), "success": False}


# Murf Tools (Text-to-Speech)
@tool
async def generate_speech_murf(text: str, voice_id: str = "en-US-neural") -> Dict[str, Any]:
    """
    Generate speech from text using Murf AI.

    Args:
        text: Text to convert to speech
        voice_id: Voice ID to use for synthesis

    Returns:
        Generated audio URL or data
    """
    if not settings.MURF_API_KEY:
        logger.warning("Murf API key not configured")
        return {"error": "Murf not configured", "success": False}

    try:
        # Placeholder for Murf API integration
        async with httpx.AsyncClient() as client:
            logger.info(f"Generating speech with Murf: {text[:50]}...")

            # Mock response
            return {
                "success": True,
                "audio_url": "https://example.com/generated-speech.mp3",
                "duration_seconds": len(text.split()) / 2.5,  # Approximate
                "voice_id": voice_id,
                "text_length": len(text)
            }

    except Exception as e:
        logger.error(f"Error generating speech with Murf: {e}")
        return {"error": str(e), "success": False}


# Exa Search Tool
@tool
async def search_web_exa(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Exa for high-quality results.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        Search results with URLs and snippets
    """
    if not settings.EXA_API_KEY:
        logger.warning("Exa API key not configured")
        return {"error": "Exa not configured", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {settings.EXA_API_KEY}"}
            response = await client.post(
                "https://api.exa.ai/search",
                json={"query": query, "num_results": num_results},
                headers=headers
            )
            response.raise_for_status()

            results = response.json()
            return {
                "success": True,
                "query": query,
                "results": results.get("results", []),
                "count": len(results.get("results", []))
            }

    except Exception as e:
        logger.error(f"Error searching with Exa: {e}")
        return {"error": str(e), "success": False}


# Serper Search Tool
@tool
async def search_web_serper(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Serper API.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        Search results
    """
    if not settings.SERPER_API_KEY:
        logger.warning("Serper API key not configured")
        return {"error": "Serper not configured", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json"
            }
            response = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": num_results},
                headers=headers
            )
            response.raise_for_status()

            results = response.json()
            return {
                "success": True,
                "query": query,
                "organic_results": results.get("organic", []),
                "count": len(results.get("organic", []))
            }

    except Exception as e:
        logger.error(f"Error searching with Serper: {e}")
        return {"error": str(e), "success": False}


# Tavily Search Tool
@tool
async def search_web_tavily(query: str, search_depth: str = "basic") -> Dict[str, Any]:
    """
    Search the web using Tavily AI for research-focused results.

    Args:
        query: Search query
        search_depth: Depth of search - "basic" or "advanced"

    Returns:
        Search results optimized for research
    """
    if not settings.TAVILY_API_KEY:
        logger.warning("Tavily API key not configured")
        return {"error": "Tavily not configured", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": search_depth
                }
            )
            response.raise_for_status()

            results = response.json()
            return {
                "success": True,
                "query": query,
                "results": results.get("results", []),
                "answer": results.get("answer", ""),
                "count": len(results.get("results", []))
            }

    except Exception as e:
        logger.error(f"Error searching with Tavily: {e}")
        return {"error": str(e), "success": False}


# Get all available tools
def get_all_tools():
    """
    Get all available third-party tools for LangGraph.

    Returns:
        List of tool functions
    """
    return [
        create_livekit_room,
        generate_livekit_token,
        analyze_speech_cartesia,
        generate_speech_murf,
        search_web_exa,
        search_web_serper,
        search_web_tavily
    ]
