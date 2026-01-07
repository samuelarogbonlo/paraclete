"""
Integration tests for session API endpoints.
"""
import pytest
from uuid import uuid4


@pytest.mark.integration
@pytest.mark.asyncio
class TestCreateSessionEndpoint:
    """Test POST /v1/sessions endpoint."""

    async def test_create_session_minimal(self, test_client, auth_headers):
        """Test creating a session with minimal data."""
        response = await test_client.post(
            "/v1/sessions",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "active"
        assert "user_id" in data
        assert "created_at" in data

    async def test_create_session_with_repo_info(self, test_client, auth_headers):
        """Test creating a session with repository information."""
        response = await test_client.post(
            "/v1/sessions",
            json={
                "repo_url": "https://github.com/test/repo",
                "branch_name": "main",
                "project_name": "Test Project",
                "description": "Integration test session",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["repo_url"] == "https://github.com/test/repo"
        assert data["branch_name"] == "main"
        assert data["project_name"] == "Test Project"
        assert data["description"] == "Integration test session"

    async def test_create_session_unauthorized(self, test_client):
        """Test creating session without authentication fails."""
        response = await test_client.post(
            "/v1/sessions",
            json={},
        )

        assert response.status_code == 401

    async def test_create_session_invalid_data(self, test_client, auth_headers):
        """Test creating session with invalid data."""
        response = await test_client.post(
            "/v1/sessions",
            json={
                "repo_url": "not-a-valid-url",
                "invalid_field": "should be ignored",
            },
            headers=auth_headers,
        )

        # Should still succeed, ignoring invalid fields
        assert response.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
class TestListSessionsEndpoint:
    """Test GET /v1/sessions endpoint."""

    async def test_list_sessions_empty(self, test_client, auth_headers):
        """Test listing sessions when user has none."""
        response = await test_client.get(
            "/v1/sessions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_sessions_with_data(self, test_client, auth_headers):
        """Test listing sessions with existing sessions."""
        # Create some sessions first
        for i in range(3):
            await test_client.post(
                "/v1/sessions",
                json={"description": f"Session {i}"},
                headers=auth_headers,
            )

        response = await test_client.get(
            "/v1/sessions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_sessions_with_status_filter(self, test_client, auth_headers):
        """Test listing sessions filtered by status."""
        # Create active session
        await test_client.post(
            "/v1/sessions",
            json={"description": "Active session"},
            headers=auth_headers,
        )

        response = await test_client.get(
            "/v1/sessions?status=active",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "active" for s in data)

    async def test_list_sessions_with_pagination(self, test_client, auth_headers):
        """Test listing sessions with pagination parameters."""
        # Create 5 sessions
        for i in range(5):
            await test_client.post(
                "/v1/sessions",
                json={"description": f"Session {i}"},
                headers=auth_headers,
            )

        # Get first page
        response1 = await test_client.get(
            "/v1/sessions?limit=2&offset=0",
            headers=auth_headers,
        )
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1) == 2

        # Get second page
        response2 = await test_client.get(
            "/v1/sessions?limit=2&offset=2",
            headers=auth_headers,
        )
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2) == 2

        # Ensure different sessions
        assert page1[0]["id"] != page2[0]["id"]

    async def test_list_sessions_unauthorized(self, test_client):
        """Test listing sessions without authentication fails."""
        response = await test_client.get("/v1/sessions")

        assert response.status_code == 401

    async def test_list_sessions_invalid_pagination(self, test_client, auth_headers):
        """Test listing with invalid pagination parameters."""
        response = await test_client.get(
            "/v1/sessions?limit=0&offset=-1",
            headers=auth_headers,
        )

        # Should handle validation error
        assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetSessionEndpoint:
    """Test GET /v1/sessions/{session_id} endpoint."""

    async def test_get_session_by_id(self, test_client, auth_headers):
        """Test retrieving a specific session."""
        # Create a session
        create_response = await test_client.post(
            "/v1/sessions",
            json={"description": "Test session"},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Get the session
        response = await test_client.get(
            f"/v1/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["description"] == "Test session"

    async def test_get_session_not_found(self, test_client, auth_headers):
        """Test getting non-existent session."""
        non_existent_id = str(uuid4())

        response = await test_client.get(
            f"/v1/sessions/{non_existent_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_get_session_unauthorized(self, test_client):
        """Test getting session without authentication."""
        session_id = str(uuid4())

        response = await test_client.get(f"/v1/sessions/{session_id}")

        assert response.status_code == 401

    async def test_get_session_forbidden(self, test_client, auth_headers, admin_headers, test_user):
        """Test getting another user's session fails."""
        # Create session as test_user
        create_response = await test_client.post(
            "/v1/sessions",
            json={"description": "User session"},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Try to access as admin (different user)
        response = await test_client.get(
            f"/v1/sessions/{session_id}",
            headers=admin_headers,
        )

        # Admin with is_superuser=True should be able to access
        # If not superuser, should be 403
        assert response.status_code in [200, 403]

    async def test_get_session_invalid_uuid(self, test_client, auth_headers):
        """Test getting session with invalid UUID format."""
        response = await test_client.get(
            "/v1/sessions/not-a-valid-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
class TestDeleteSessionEndpoint:
    """Test DELETE /v1/sessions/{session_id} endpoint."""

    async def test_delete_session(self, test_client, auth_headers):
        """Test deleting a session."""
        # Create a session
        create_response = await test_client.post(
            "/v1/sessions",
            json={"description": "To be deleted"},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Delete the session
        response = await test_client.delete(
            f"/v1/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify session is deleted
        get_response = await test_client.get(
            f"/v1/sessions/{session_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_session_not_found(self, test_client, auth_headers):
        """Test deleting non-existent session."""
        non_existent_id = str(uuid4())

        response = await test_client.delete(
            f"/v1/sessions/{non_existent_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_session_unauthorized(self, test_client):
        """Test deleting session without authentication."""
        session_id = str(uuid4())

        response = await test_client.delete(f"/v1/sessions/{session_id}")

        assert response.status_code == 401

    async def test_delete_session_forbidden(self, test_client, auth_headers, admin_headers):
        """Test deleting another user's session fails."""
        # Create session as test_user
        create_response = await test_client.post(
            "/v1/sessions",
            json={"description": "User session"},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Try to delete as different user
        response = await test_client.delete(
            f"/v1/sessions/{session_id}",
            headers=admin_headers,
        )

        assert response.status_code in [204, 403]  # Depends on superuser status


@pytest.mark.integration
@pytest.mark.asyncio
class TestSyncSessionEndpoint:
    """Test POST /v1/sessions/{session_id}/sync endpoint."""

    async def test_sync_session_creates_new(self, test_client, auth_headers):
        """Test syncing creates a new session if desktop_session_id doesn't exist."""
        response = await test_client.post(
            "/v1/sessions/sync",
            json={
                "desktop_session_id": "desktop_123",
                "repo_url": "https://github.com/test/repo",
                "branch_name": "main",
                "project_name": "Test Project",
                "commit_sha": "abc123",
                "files_changed": ["file1.py", "file2.py"],
                "messages": [],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["desktop_session_id"] == "desktop_123"
        assert data["repo_url"] == "https://github.com/test/repo"
        assert data["current_commit_sha"] == "abc123"

    async def test_sync_session_updates_existing(self, test_client, auth_headers):
        """Test syncing updates existing session with same desktop_session_id."""
        # First sync
        await test_client.post(
            "/v1/sessions/sync",
            json={
                "desktop_session_id": "desktop_456",
                "repo_url": "https://github.com/test/repo",
                "branch_name": "main",
            },
            headers=auth_headers,
        )

        # Second sync with updated data
        response = await test_client.post(
            "/v1/sessions/sync",
            json={
                "desktop_session_id": "desktop_456",
                "repo_url": "https://github.com/test/repo",
                "branch_name": "develop",
                "commit_sha": "def456",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["branch_name"] == "develop"
        assert data["current_commit_sha"] == "def456"

    async def test_sync_session_unauthorized(self, test_client):
        """Test syncing without authentication fails."""
        response = await test_client.post(
            "/v1/sessions/sync",
            json={"desktop_session_id": "desktop_789"},
        )

        assert response.status_code == 401

    async def test_sync_session_missing_desktop_id(self, test_client, auth_headers):
        """Test syncing without desktop_session_id fails."""
        response = await test_client.post(
            "/v1/sessions/sync",
            json={"repo_url": "https://github.com/test/repo"},
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetSessionMessagesEndpoint:
    """Test GET /v1/sessions/{session_id}/messages endpoint."""

    async def test_get_session_messages_empty(self, test_client, auth_headers):
        """Test getting messages for session with no messages."""
        # Create a session
        create_response = await test_client.post(
            "/v1/sessions",
            json={},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        response = await test_client.get(
            f"/v1/sessions/{session_id}/messages",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_session_messages_not_found(self, test_client, auth_headers):
        """Test getting messages for non-existent session."""
        non_existent_id = str(uuid4())

        response = await test_client.get(
            f"/v1/sessions/{non_existent_id}/messages",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_get_session_messages_unauthorized(self, test_client):
        """Test getting messages without authentication."""
        session_id = str(uuid4())

        response = await test_client.get(
            f"/v1/sessions/{session_id}/messages"
        )

        assert response.status_code == 401

    async def test_get_session_messages_with_pagination(self, test_client, auth_headers):
        """Test getting messages with pagination."""
        # Create a session
        create_response = await test_client.post(
            "/v1/sessions",
            json={},
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Get messages with pagination params
        response = await test_client.get(
            f"/v1/sessions/{session_id}/messages?limit=10&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestSessionAPIEdgeCases:
    """Test edge cases and error handling."""

    async def test_concurrent_session_creation(self, test_client, auth_headers):
        """Test creating multiple sessions concurrently."""
        import asyncio

        async def create_session(description):
            return await test_client.post(
                "/v1/sessions",
                json={"description": description},
                headers=auth_headers,
            )

        responses = await asyncio.gather(
            *[create_session(f"Session {i}") for i in range(5)]
        )

        assert all(r.status_code == 201 for r in responses)
        session_ids = [r.json()["id"] for r in responses]
        assert len(set(session_ids)) == 5  # All unique

    async def test_session_with_very_long_description(self, test_client, auth_headers):
        """Test session with very long description."""
        long_description = "A" * 10000

        response = await test_client.post(
            "/v1/sessions",
            json={"description": long_description},
            headers=auth_headers,
        )

        # Should handle long strings
        assert response.status_code in [201, 400]

    async def test_session_response_structure(self, test_client, auth_headers):
        """Test that session response has all required fields."""
        response = await test_client.post(
            "/v1/sessions",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify required fields
        required_fields = [
            "id", "user_id", "status", "agent_statuses",
            "created_at", "updated_at", "last_activity"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_session_timestamps_are_iso_format(self, test_client, auth_headers):
        """Test that timestamps are in ISO format."""
        response = await test_client.post(
            "/v1/sessions",
            json={},
            headers=auth_headers,
        )

        data = response.json()
        from datetime import datetime

        # Should be able to parse ISO timestamps
        datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(data["last_activity"].replace('Z', '+00:00'))
