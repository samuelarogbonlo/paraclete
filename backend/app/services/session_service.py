"""
Session management service.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
import logging

from app.db.models import Session, User, Message, SessionStatus, MessageRole
from app.core.exceptions import NotFoundError, AuthorizationError, SessionError

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user sessions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize session service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_session(
        self,
        user: User,
        repo_url: Optional[str] = None,
        branch_name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        desktop_session_id: Optional[str] = None,
    ) -> Session:
        """
        Create a new coding session.

        Args:
            user: User creating the session
            repo_url: Optional repository URL
            branch_name: Optional branch name
            project_name: Optional project name
            description: Optional session description
            desktop_session_id: Optional desktop session ID for syncing

        Returns:
            Created session
        """
        session = Session(
            user_id=user.id,
            status=SessionStatus.ACTIVE,
            repo_url=repo_url,
            branch_name=branch_name,
            project_name=project_name or self._extract_project_name(repo_url),
            description=description,
            desktop_session_id=desktop_session_id,
            agent_statuses={},
            files_changed=[],
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"Created session {session.id} for user {user.id}")
        return session

    async def get_session(
        self, session_id: UUID, user: Optional[User] = None
    ) -> Session:
        """
        Get a session by ID.

        Args:
            session_id: Session ID
            user: Optional user for authorization check

        Returns:
            Session object

        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        result = await self.db.execute(
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise NotFoundError("Session", str(session_id))

        if user and session.user_id != user.id and not user.is_superuser:
            raise AuthorizationError("You don't have access to this session")

        return session

    async def list_user_sessions(
        self,
        user: User,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """
        List user's sessions.

        Args:
            user: User whose sessions to list
            status: Optional status filter
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of sessions
        """
        query = select(Session).where(Session.user_id == user.id)

        if status:
            query = query.where(Session.status == status)

        query = (
            query.order_by(desc(Session.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_session(
        self,
        session_id: UUID,
        user: User,
        updates: Dict[str, Any],
    ) -> Session:
        """
        Update a session.

        Args:
            session_id: Session ID
            user: User performing the update
            updates: Dictionary of fields to update

        Returns:
            Updated session

        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        session = await self.get_session(session_id, user)

        # Update allowed fields
        allowed_fields = {
            "status",
            "repo_url",
            "branch_name",
            "project_name",
            "description",
            "current_agent",
            "agent_statuses",
            "current_commit_sha",
            "files_changed",
            "vm_machine_id",
            "vm_status",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(session, field):
                setattr(session, field, value)

        # Update timestamps
        session.updated_at = datetime.utcnow()
        if "status" in updates and updates["status"] == SessionStatus.COMPLETED:
            session.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"Updated session {session_id}")
        return session

    async def delete_session(self, session_id: UUID, user: User) -> None:
        """
        Delete a session and all its messages.

        Args:
            session_id: Session ID
            user: User performing the deletion

        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        session = await self.get_session(session_id, user)

        await self.db.delete(session)
        await self.db.commit()

        logger.info(f"Deleted session {session_id}")

    async def sync_from_desktop(
        self,
        user: User,
        desktop_session_id: str,
        context: Dict[str, Any],
    ) -> Session:
        """
        Sync session from desktop (Claude Code, Cursor, etc).

        Args:
            user: User syncing the session
            desktop_session_id: Desktop session identifier
            context: Session context from desktop

        Returns:
            Synced or created session
        """
        # Check if session already exists
        result = await self.db.execute(
            select(Session).where(
                and_(
                    Session.user_id == user.id,
                    Session.desktop_session_id == desktop_session_id,
                )
            )
        )
        session = result.scalar_one_or_none()

        if session:
            # Update existing session
            updates = {
                "repo_url": context.get("repo_url", session.repo_url),
                "branch_name": context.get("branch_name", session.branch_name),
                "current_commit_sha": context.get("commit_sha"),
                "files_changed": context.get("files_changed", []),
            }
            session = await self.update_session(session.id, user, updates)
        else:
            # Create new session
            session = await self.create_session(
                user=user,
                repo_url=context.get("repo_url"),
                branch_name=context.get("branch_name"),
                project_name=context.get("project_name"),
                description=f"Synced from desktop: {desktop_session_id}",
                desktop_session_id=desktop_session_id,
            )

        # Add messages from desktop context if provided
        if "messages" in context:
            await self._add_messages_to_session(session, context["messages"])

        logger.info(f"Synced session {session.id} from desktop {desktop_session_id}")
        return session

    async def add_message(
        self,
        session_id: UUID,
        user: User,
        role: MessageRole,
        content: str,
        voice_transcript: Optional[str] = None,
        agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            user: User adding the message
            role: Message role (user, assistant, system)
            content: Message content
            voice_transcript: Optional voice transcript
            agent: Optional agent name
            metadata: Optional metadata

        Returns:
            Created message

        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        session = await self.get_session(session_id, user)

        message = Message(
            session_id=session.id,
            role=role,
            content=content,
            voice_transcript=voice_transcript,
            agent=agent,
            metadata=metadata or {},
        )

        self.db.add(message)

        # Update session last activity
        session.last_activity = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(message)

        logger.debug(f"Added message to session {session_id}")
        return message

    async def get_session_messages(
        self,
        session_id: UUID,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """
        Get messages for a session.

        Args:
            session_id: Session ID
            user: User requesting messages
            limit: Maximum number of messages
            offset: Number of messages to skip

        Returns:
            List of messages

        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        session = await self.get_session(session_id, user)

        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.timestamp)
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all()

    def _extract_project_name(self, repo_url: Optional[str]) -> Optional[str]:
        """
        Extract project name from repository URL.

        Args:
            repo_url: Repository URL

        Returns:
            Project name or None
        """
        if not repo_url:
            return None

        # Extract from GitHub/GitLab URLs
        parts = repo_url.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-1].replace(".git", "")

        return None

    async def _add_messages_to_session(
        self, session: Session, messages: List[Dict[str, Any]]
    ) -> None:
        """
        Bulk add messages to a session.

        Args:
            session: Session to add messages to
            messages: List of message dictionaries
        """
        for msg_data in messages:
            message = Message(
                session_id=session.id,
                role=MessageRole(msg_data.get("role", "user")),
                content=msg_data.get("content", ""),
                agent=msg_data.get("agent"),
                metadata=msg_data.get("metadata", {}),
            )
            self.db.add(message)

        await self.db.commit()