"""
Unit tests for SessionService.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.services.session_service import SessionService
from app.db.models import SessionStatus, MessageRole
from app.core.exceptions import NotFoundError, AuthorizationError


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceCreate:
    """Test session creation."""

    async def test_create_session_minimal(self, db_session, test_user):
        """Test creating a session with minimal data."""
        service = SessionService(db_session)

        session = await service.create_session(user=test_user)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.status == SessionStatus.ACTIVE
        assert session.repo_url is None
        assert session.branch_name is None
        assert session.agent_statuses == {}
        assert session.files_changed == []

    async def test_create_session_with_repo(self, db_session, test_user):
        """Test creating a session with repository URL."""
        service = SessionService(db_session)

        session = await service.create_session(
            user=test_user,
            repo_url="https://github.com/test/repo",
            branch_name="main",
        )

        assert session.repo_url == "https://github.com/test/repo"
        assert session.branch_name == "main"

    async def test_create_session_with_all_fields(self, db_session, test_user):
        """Test creating a session with all optional fields."""
        service = SessionService(db_session)

        session = await service.create_session(
            user=test_user,
            repo_url="https://github.com/test/repo",
            branch_name="feature/test",
            project_name="Custom Project",
            description="Test description",
            desktop_session_id="desktop_123",
        )

        assert session.repo_url == "https://github.com/test/repo"
        assert session.branch_name == "feature/test"
        assert session.project_name == "Custom Project"
        assert session.description == "Test description"
        assert session.desktop_session_id == "desktop_123"

    async def test_create_session_extracts_project_name(self, db_session, test_user):
        """Test that project name is extracted from repo URL if not provided."""
        service = SessionService(db_session)

        session = await service.create_session(
            user=test_user,
            repo_url="https://github.com/test/my-awesome-repo",
        )

        assert session.project_name == "my-awesome-repo"

    async def test_create_session_with_git_extension(self, db_session, test_user):
        """Test project name extraction removes .git extension."""
        service = SessionService(db_session)

        session = await service.create_session(
            user=test_user,
            repo_url="https://github.com/test/my-repo.git",
        )

        assert session.project_name == "my-repo"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceRetrieve:
    """Test session retrieval."""

    async def test_get_session_by_id(self, db_session, test_user, test_session):
        """Test retrieving a session by ID."""
        service = SessionService(db_session)

        session = await service.get_session(test_session.id, test_user)

        assert session.id == test_session.id
        assert session.user_id == test_user.id

    async def test_get_session_not_found(self, db_session, test_user):
        """Test retrieving non-existent session raises error."""
        service = SessionService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await service.get_session(non_existent_id, test_user)

        assert "Session" in str(exc_info.value)

    async def test_get_session_unauthorized(self, db_session, test_user, test_session, admin_user):
        """Test retrieving another user's session raises error."""
        service = SessionService(db_session)

        # test_session belongs to test_user, try to access with admin_user (who is not superuser in this context)
        with pytest.raises(AuthorizationError) as exc_info:
            await service.get_session(test_session.id, admin_user)

        assert "access" in str(exc_info.value).lower()

    async def test_get_session_as_superuser(self, db_session, test_session, admin_user):
        """Test superuser can access any session."""
        service = SessionService(db_session)

        # Admin user has is_superuser=True
        session = await service.get_session(test_session.id, admin_user)

        assert session.id == test_session.id

    async def test_list_user_sessions(self, db_session, test_user):
        """Test listing user's sessions."""
        service = SessionService(db_session)

        # Create multiple sessions
        await service.create_session(user=test_user, description="Session 1")
        await service.create_session(user=test_user, description="Session 2")
        await service.create_session(user=test_user, description="Session 3")

        sessions = await service.list_user_sessions(user=test_user)

        assert len(sessions) == 3
        assert all(s.user_id == test_user.id for s in sessions)

    async def test_list_user_sessions_with_status_filter(self, db_session, test_user):
        """Test listing sessions filtered by status."""
        service = SessionService(db_session)

        # Create sessions with different statuses
        session1 = await service.create_session(user=test_user)
        session2 = await service.create_session(user=test_user)

        # Update one session to completed
        await service.update_session(
            session2.id,
            test_user,
            {"status": SessionStatus.COMPLETED}
        )

        active_sessions = await service.list_user_sessions(
            user=test_user,
            status=SessionStatus.ACTIVE
        )

        assert len(active_sessions) == 1
        assert active_sessions[0].id == session1.id

    async def test_list_user_sessions_with_pagination(self, db_session, test_user):
        """Test listing sessions with pagination."""
        service = SessionService(db_session)

        # Create 5 sessions
        for i in range(5):
            await service.create_session(user=test_user, description=f"Session {i}")

        # Get first page
        page1 = await service.list_user_sessions(user=test_user, limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await service.list_user_sessions(user=test_user, limit=2, offset=2)
        assert len(page2) == 2

        # Ensure different sessions
        assert page1[0].id != page2[0].id

    async def test_list_user_sessions_ordered_by_created_at(self, db_session, test_user):
        """Test that sessions are ordered by creation date (newest first)."""
        service = SessionService(db_session)

        session1 = await service.create_session(user=test_user, description="First")
        session2 = await service.create_session(user=test_user, description="Second")

        sessions = await service.list_user_sessions(user=test_user)

        # Newest first
        assert sessions[0].id == session2.id
        assert sessions[1].id == session1.id


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceUpdate:
    """Test session updates."""

    async def test_update_session_status(self, db_session, test_user, test_session):
        """Test updating session status."""
        service = SessionService(db_session)

        updated = await service.update_session(
            test_session.id,
            test_user,
            {"status": SessionStatus.PAUSED}
        )

        assert updated.status == SessionStatus.PAUSED

    async def test_update_session_repo_info(self, db_session, test_user, test_session):
        """Test updating repository information."""
        service = SessionService(db_session)

        updated = await service.update_session(
            test_session.id,
            test_user,
            {
                "repo_url": "https://github.com/new/repo",
                "branch_name": "develop",
            }
        )

        assert updated.repo_url == "https://github.com/new/repo"
        assert updated.branch_name == "develop"

    async def test_update_session_multiple_fields(self, db_session, test_user, test_session):
        """Test updating multiple fields at once."""
        service = SessionService(db_session)

        updated = await service.update_session(
            test_session.id,
            test_user,
            {
                "status": SessionStatus.PAUSED,
                "description": "Updated description",
                "current_agent": "coder",
                "agent_statuses": {"coder": "active"},
            }
        )

        assert updated.status == SessionStatus.PAUSED
        assert updated.description == "Updated description"
        assert updated.current_agent == "coder"
        assert updated.agent_statuses == {"coder": "active"}

    async def test_update_session_sets_completed_at(self, db_session, test_user, test_session):
        """Test that updating to completed sets completed_at timestamp."""
        service = SessionService(db_session)

        updated = await service.update_session(
            test_session.id,
            test_user,
            {"status": SessionStatus.COMPLETED}
        )

        assert updated.status == SessionStatus.COMPLETED
        assert updated.completed_at is not None
        assert isinstance(updated.completed_at, datetime)

    async def test_update_session_ignores_disallowed_fields(self, db_session, test_user, test_session):
        """Test that disallowed fields are ignored."""
        service = SessionService(db_session)
        original_id = test_session.id

        updated = await service.update_session(
            test_session.id,
            test_user,
            {
                "id": uuid4(),  # Should be ignored
                "user_id": uuid4(),  # Should be ignored
                "created_at": datetime.utcnow(),  # Should be ignored
                "description": "New description",  # Should be updated
            }
        )

        assert updated.id == original_id
        assert updated.user_id == test_user.id
        assert updated.description == "New description"

    async def test_update_session_unauthorized(self, db_session, test_session, admin_user):
        """Test updating another user's session raises error."""
        service = SessionService(db_session)

        with pytest.raises(AuthorizationError):
            await service.update_session(
                test_session.id,
                admin_user,
                {"description": "Hacked!"}
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceDelete:
    """Test session deletion."""

    async def test_delete_session(self, db_session, test_user, test_session):
        """Test deleting a session."""
        service = SessionService(db_session)
        session_id = test_session.id

        await service.delete_session(session_id, test_user)

        # Verify session is deleted
        with pytest.raises(NotFoundError):
            await service.get_session(session_id, test_user)

    async def test_delete_session_unauthorized(self, db_session, test_session, admin_user):
        """Test deleting another user's session raises error."""
        service = SessionService(db_session)

        with pytest.raises(AuthorizationError):
            await service.delete_session(test_session.id, admin_user)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceSync:
    """Test desktop session synchronization."""

    async def test_sync_creates_new_session(self, db_session, test_user):
        """Test syncing creates a new session if it doesn't exist."""
        service = SessionService(db_session)

        context = {
            "repo_url": "https://github.com/test/repo",
            "branch_name": "main",
            "project_name": "Test Project",
            "commit_sha": "abc123",
            "files_changed": ["file1.py", "file2.py"],
        }

        session = await service.sync_from_desktop(
            user=test_user,
            desktop_session_id="desktop_123",
            context=context,
        )

        assert session.desktop_session_id == "desktop_123"
        assert session.repo_url == "https://github.com/test/repo"
        assert session.branch_name == "main"
        assert session.current_commit_sha == "abc123"
        assert "file1.py" in session.files_changed

    async def test_sync_updates_existing_session(self, db_session, test_user):
        """Test syncing updates existing session with same desktop_session_id."""
        service = SessionService(db_session)

        # Create initial session
        context1 = {
            "repo_url": "https://github.com/test/repo",
            "branch_name": "main",
        }
        session1 = await service.sync_from_desktop(
            user=test_user,
            desktop_session_id="desktop_123",
            context=context1,
        )

        # Sync again with updated context
        context2 = {
            "repo_url": "https://github.com/test/repo",
            "branch_name": "develop",
            "commit_sha": "def456",
            "files_changed": ["file3.py"],
        }
        session2 = await service.sync_from_desktop(
            user=test_user,
            desktop_session_id="desktop_123",
            context=context2,
        )

        # Should be same session, updated
        assert session1.id == session2.id
        assert session2.branch_name == "develop"
        assert session2.current_commit_sha == "def456"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionServiceMessages:
    """Test message management."""

    async def test_add_message_to_session(self, db_session, test_user, test_session):
        """Test adding a message to a session."""
        service = SessionService(db_session)

        message = await service.add_message(
            session_id=test_session.id,
            user=test_user,
            role=MessageRole.USER,
            content="Test message",
        )

        assert message.id is not None
        assert message.session_id == test_session.id
        assert message.role == MessageRole.USER
        assert message.content == "Test message"

    async def test_add_message_with_voice_transcript(self, db_session, test_user, test_session):
        """Test adding a message with voice transcript."""
        service = SessionService(db_session)

        message = await service.add_message(
            session_id=test_session.id,
            user=test_user,
            role=MessageRole.USER,
            content="Test message",
            voice_transcript="Original voice input",
        )

        assert message.voice_transcript == "Original voice input"

    async def test_add_message_with_agent(self, db_session, test_user, test_session):
        """Test adding a message from an agent."""
        service = SessionService(db_session)

        message = await service.add_message(
            session_id=test_session.id,
            user=test_user,
            role=MessageRole.ASSISTANT,
            content="Agent response",
            agent="coder",
        )

        assert message.agent == "coder"
        assert message.role == MessageRole.ASSISTANT

    async def test_add_message_with_metadata(self, db_session, test_user, test_session):
        """Test adding a message with metadata."""
        service = SessionService(db_session)

        metadata = {"key": "value", "count": 42}
        message = await service.add_message(
            session_id=test_session.id,
            user=test_user,
            role=MessageRole.SYSTEM,
            content="System message",
            metadata=metadata,
        )

        assert message.metadata == metadata

    async def test_get_session_messages(self, db_session, test_user, test_session):
        """Test retrieving messages for a session."""
        service = SessionService(db_session)

        # Add multiple messages
        await service.add_message(
            test_session.id, test_user, MessageRole.USER, "Message 1"
        )
        await service.add_message(
            test_session.id, test_user, MessageRole.ASSISTANT, "Message 2"
        )
        await service.add_message(
            test_session.id, test_user, MessageRole.USER, "Message 3"
        )

        messages = await service.get_session_messages(
            session_id=test_session.id,
            user=test_user,
        )

        assert len(messages) == 3
        assert messages[0].content == "Message 1"  # Ordered by timestamp
        assert messages[1].content == "Message 2"
        assert messages[2].content == "Message 3"

    async def test_get_session_messages_with_pagination(self, db_session, test_user, test_session):
        """Test retrieving messages with pagination."""
        service = SessionService(db_session)

        # Add 5 messages
        for i in range(5):
            await service.add_message(
                test_session.id, test_user, MessageRole.USER, f"Message {i}"
            )

        # Get first page
        page1 = await service.get_session_messages(
            session_id=test_session.id,
            user=test_user,
            limit=2,
            offset=0,
        )

        assert len(page1) == 2

        # Get second page
        page2 = await service.get_session_messages(
            session_id=test_session.id,
            user=test_user,
            limit=2,
            offset=2,
        )

        assert len(page2) == 2
        assert page1[0].id != page2[0].id


@pytest.mark.unit
class TestSessionServiceHelpers:
    """Test helper methods."""

    def test_extract_project_name_from_github_url(self):
        """Test extracting project name from GitHub URL."""
        service = SessionService(None)

        name = service._extract_project_name("https://github.com/user/my-project")
        assert name == "my-project"

    def test_extract_project_name_removes_git_extension(self):
        """Test that .git extension is removed."""
        service = SessionService(None)

        name = service._extract_project_name("https://github.com/user/my-project.git")
        assert name == "my-project"

    def test_extract_project_name_from_gitlab_url(self):
        """Test extracting from GitLab URL."""
        service = SessionService(None)

        name = service._extract_project_name("https://gitlab.com/user/my-project")
        assert name == "my-project"

    def test_extract_project_name_returns_none_for_invalid(self):
        """Test that invalid URLs return None."""
        service = SessionService(None)

        assert service._extract_project_name(None) is None
        assert service._extract_project_name("") is None
        assert service._extract_project_name("invalid") is None
