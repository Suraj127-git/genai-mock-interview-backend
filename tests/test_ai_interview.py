"""
Tests for AI interview API endpoints.
"""
import pytest
from datetime import datetime
from httpx import AsyncClient

from app.main import app


@pytest.mark.ai_interview
class TestAIInterviewProfile:
    """Tests for user profile endpoints."""

    async def test_create_profile(self, client: AsyncClient, auth_headers: dict):
        """Test creating user profile."""
        profile_data = {
            "current_role": "Software Engineer",
            "current_company": "Tech Corp",
            "years_of_experience": 5,
            "target_role": "Senior Software Engineer",
            "target_companies": ["Google", "Meta", "Amazon"],
            "technical_skills": ["Python", "React", "AWS", "Docker"],
            "soft_skills": ["Leadership", "Communication", "Problem Solving"],
            "difficulty_preference": "medium",
            "bio": "Experienced software engineer with focus on backend development"
        }

        response = await client.post(
            "/ai-interview/profile",
            json=profile_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["current_role"] == profile_data["current_role"]
        assert data["target_role"] == profile_data["target_role"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_profile(self, client: AsyncClient, auth_headers: dict):
        """Test getting user profile."""
        response = await client.get(
            "/ai-interview/profile",
            headers=auth_headers
        )

        assert response.status_code in [200, 404]  # 404 if profile doesn't exist yet

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "user_id" in data

    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        # First create profile
        await client.post(
            "/ai-interview/profile",
            json={"current_role": "Engineer"},
            headers=auth_headers
        )

        # Update profile
        update_data = {
            "years_of_experience": 6,
            "technical_skills": ["Python", "Go", "Kubernetes"]
        }

        response = await client.put(
            "/ai-interview/profile",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["years_of_experience"] == 6

    async def test_index_profile(self, client: AsyncClient, auth_headers: dict):
        """Test RAG indexing of profile."""
        response = await client.post(
            "/ai-interview/profile/index",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "user_id" in data


@pytest.mark.ai_interview
class TestAIInterviewSession:
    """Tests for AI interview session endpoints."""

    async def test_start_interview(self, client: AsyncClient, auth_headers: dict):
        """Test starting an AI interview session."""
        session_data = {
            "title": "Technical Interview Practice",
            "interview_type": "technical",
            "role_context": "Senior Software Engineer",
            "company_context": "Google",
            "difficulty_level": "hard"
        }

        response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "response" in data
        assert data["status"] == "active" or data["status"] == "initializing"
        assert len(data["response"]) > 0

        return data["session_id"]

    async def test_list_sessions(self, client: AsyncClient, auth_headers: dict):
        """Test listing interview sessions."""
        response = await client.get(
            "/ai-interview/sessions",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_session_detail(self, client: AsyncClient, auth_headers: dict):
        """Test getting session details."""
        # Start a session first
        session_data = {
            "title": "Test Interview",
            "interview_type": "general"
        }

        create_response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        session_id = create_response.json()["session_id"]

        # Get session details
        response = await client.get(
            f"/ai-interview/sessions/{session_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "interactions" in data
        assert isinstance(data["interactions"], list)

    async def test_send_message(self, client: AsyncClient, auth_headers: dict):
        """Test sending message in interview."""
        # Start session
        session_data = {
            "title": "Message Test Interview",
            "interview_type": "behavioral"
        }

        create_response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        session_id = create_response.json()["session_id"]

        # Send message
        message_data = {
            "message": "I led a team of 5 engineers to deliver a critical project. We used Agile methodologies and completed it 2 weeks ahead of schedule."
        }

        response = await client.post(
            f"/ai-interview/sessions/{session_id}/message",
            json=message_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0

    async def test_complete_interview(self, client: AsyncClient, auth_headers: dict):
        """Test completing interview and getting assessment."""
        # Start session
        session_data = {
            "title": "Complete Test Interview",
            "interview_type": "technical"
        }

        create_response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        session_id = create_response.json()["session_id"]

        # Send a few messages
        await client.post(
            f"/ai-interview/sessions/{session_id}/message",
            json={"message": "I would use a binary search algorithm"},
            headers=auth_headers
        )

        await client.post(
            f"/ai-interview/sessions/{session_id}/message",
            json={"message": "The time complexity would be O(log n)"},
            headers=auth_headers
        )

        # Complete interview
        response = await client.post(
            f"/ai-interview/sessions/{session_id}/complete",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "completed_at" in data

    async def test_assess_session(self, client: AsyncClient, auth_headers: dict):
        """Test assessment generation."""
        # Create and complete a session
        session_data = {
            "title": "Assessment Test",
            "interview_type": "behavioral"
        }

        create_response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        session_id = create_response.json()["session_id"]

        # Add some interactions
        await client.post(
            f"/ai-interview/sessions/{session_id}/message",
            json={"message": "In my previous role, I identified a bottleneck in our deployment process..."},
            headers=auth_headers
        )

        # Complete session
        await client.post(
            f"/ai-interview/sessions/{session_id}/complete",
            headers=auth_headers
        )

        # Request assessment
        response = await client.post(
            f"/ai-interview/sessions/{session_id}/assess",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "communication_scores" in data
        assert "content_scores" in data
        assert "feedback" in data


@pytest.mark.ai_interview
class TestAIInterviewTypes:
    """Test different interview types."""

    @pytest.mark.parametrize("interview_type", [
        "behavioral",
        "technical",
        "case",
        "system_design",
        "general"
    ])
    async def test_different_interview_types(
        self,
        client: AsyncClient,
        auth_headers: dict,
        interview_type: str
    ):
        """Test starting interviews of different types."""
        session_data = {
            "title": f"{interview_type.title()} Interview Test",
            "interview_type": interview_type
        }

        response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data


@pytest.mark.ai_interview
class TestLiveKit:
    """Tests for LiveKit integration."""

    async def test_get_livekit_token(self, client: AsyncClient, auth_headers: dict):
        """Test getting LiveKit token."""
        response = await client.post(
            "/ai-interview/livekit/token?room_name=test-room&participant_name=TestUser",
            headers=auth_headers
        )

        # May return 200 with mock token or 503 if LiveKit not configured
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            assert "room_name" in data
            assert data["room_name"] == "test-room"


@pytest.mark.ai_interview
class TestValidation:
    """Tests for input validation."""

    async def test_invalid_interview_type(self, client: AsyncClient, auth_headers: dict):
        """Test creating session with invalid interview type."""
        session_data = {
            "title": "Invalid Type Test",
            "interview_type": "invalid_type"
        }

        response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        # Should accept any string for now, but could validate in future
        assert response.status_code in [201, 400, 422]

    async def test_missing_required_fields(self, client: AsyncClient, auth_headers: dict):
        """Test creating session without required fields."""
        session_data = {}

        response = await client.post(
            "/ai-interview/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_empty_message(self, client: AsyncClient, auth_headers: dict):
        """Test sending empty message."""
        # Create session
        create_response = await client.post(
            "/ai-interview/sessions",
            json={"title": "Test", "interview_type": "general"},
            headers=auth_headers
        )

        session_id = create_response.json()["session_id"]

        # Try to send empty message
        response = await client.post(
            f"/ai-interview/sessions/{session_id}/message",
            json={"message": ""},
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.ai_interview
class TestAuthorization:
    """Tests for authorization."""

    async def test_unauthorized_access(self, client: AsyncClient):
        """Test accessing endpoints without auth token."""
        response = await client.get("/ai-interview/profile")

        assert response.status_code == 401

    async def test_access_other_user_session(self, client: AsyncClient, auth_headers: dict):
        """Test accessing another user's session."""
        # Try to access a session that doesn't belong to user
        response = await client.get(
            "/ai-interview/sessions/99999",
            headers=auth_headers
        )

        assert response.status_code == 404


# Fixtures
@pytest.fixture
async def client():
    """Create async HTTP client."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Get authentication headers."""
    # Register and login to get token
    from faker import Faker
    fake = Faker()

    email = fake.email()
    password = "TestPassword123!"

    # Register
    await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": fake.name()
        }
    )

    # Login
    response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password
        }
    )

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}
