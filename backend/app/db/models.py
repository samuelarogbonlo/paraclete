"""
SQLAlchemy database models.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    JSON,
    Integer,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.db.database import Base


class SessionStatus(str, enum.Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class MessageRole(str, enum.Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Null for OAuth users

    # OAuth fields
    github_id = Column(String(100), unique=True, nullable=True, index=True)
    github_username = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Subscription tier
    tier = Column(String(20), default="free", nullable=False)  # free, pro, teams
    tier_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserAPIKeys", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Session(Base):
    """Session model for tracking user coding sessions."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Status
    status = Column(
        SQLEnum(SessionStatus),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )

    # Context
    repo_url = Column(Text, nullable=True)
    branch_name = Column(String(255), nullable=True)
    desktop_session_id = Column(String(255), nullable=True)  # For sync from desktop
    project_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Agent state
    langgraph_thread_id = Column(String(255), nullable=True, unique=True)
    agent_statuses = Column(JSON, nullable=False, default=dict)  # Dict[str, str]
    current_agent = Column(String(100), nullable=True)

    # Git tracking
    initial_commit_sha = Column(String(40), nullable=True)
    current_commit_sha = Column(String(40), nullable=True)
    files_changed = Column(JSON, nullable=False, default=list)  # List[str]

    # VM tracking
    vm_machine_id = Column(String(255), nullable=True)  # Fly.io machine ID
    vm_status = Column(String(50), nullable=True)  # running, stopped, terminated

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Message model for storing conversation history."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)

    # Message content
    role = Column(SQLEnum(MessageRole), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Voice data
    voice_transcript = Column(Text, nullable=True)  # Original voice input
    audio_url = Column(Text, nullable=True)  # URL to stored audio file

    # Agent tracking
    agent = Column(String(100), nullable=True)  # Which agent generated this
    agent_model = Column(String(100), nullable=True)  # Which AI model was used

    # Metadata (renamed to avoid SQLAlchemy reserved word)
    message_metadata = Column(JSON, nullable=False, default=dict)  # Additional data

    # Timestamps
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    edited_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="messages")


class UserAPIKeys(Base):
    """Encrypted API keys for users (BYOK model)."""

    __tablename__ = "user_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    # Encrypted API keys (encrypted with user's master key)
    anthropic_key_encrypted = Column(Text, nullable=True)
    openai_key_encrypted = Column(Text, nullable=True)
    google_key_encrypted = Column(Text, nullable=True)
    deepgram_key_encrypted = Column(Text, nullable=True)
    elevenlabs_key_encrypted = Column(Text, nullable=True)
    github_token_encrypted = Column(Text, nullable=True)

    # Encryption salt (Base64-encoded, unique per user)
    encryption_salt = Column(Text, nullable=True)

    # Service configuration
    using_managed_keys = Column(Boolean, default=False, nullable=False)
    default_model = Column(String(100), nullable=True)  # User's preferred model

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    user = relationship("User", back_populates="api_keys")