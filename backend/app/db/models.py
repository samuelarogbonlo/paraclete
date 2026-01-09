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


class AgentExecutionStatus(str, enum.Enum):
    """Agent execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentType(str, enum.Enum):
    """Agent type enumeration."""

    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    DESIGNER = "designer"


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


class VMStatus(str, enum.Enum):
    """VM status enumeration."""

    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    ERROR = "error"


class UserVM(Base):
    """User VM tracking for cloud compute."""

    __tablename__ = "user_vms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True
    )  # Optional link to session

    # Fly.io machine details
    machine_id = Column(String(255), unique=True, nullable=False, index=True)
    machine_name = Column(String(255), nullable=True)
    region = Column(String(50), nullable=True)  # e.g., "iad", "lax"
    machine_config = Column(JSON, nullable=False, default=dict)  # CPU, RAM, etc.

    # Status
    status = Column(
        SQLEnum(VMStatus),
        nullable=False,
        default=VMStatus.PROVISIONING,
        index=True,
    )
    status_message = Column(Text, nullable=True)

    # Networking
    ipv4_address = Column(String(45), nullable=True)
    ipv6_address = Column(String(45), nullable=True)
    tailscale_ip = Column(String(45), nullable=True)
    ssh_hostname = Column(String(255), nullable=True)
    ssh_port = Column(Integer, default=22, nullable=False)

    # Resource tracking
    cpu_type = Column(String(50), nullable=True)  # shared-cpu-1x, performance-cpu-2x
    memory_mb = Column(Integer, nullable=True)
    disk_gb = Column(Integer, nullable=True)

    # Activity tracking
    last_activity = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    auto_shutdown_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Scheduled shutdown time

    # Timestamps
    provisioned_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
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
    user = relationship("User")
    session = relationship("Session")
    compute_usage = relationship(
        "ComputeUsage", back_populates="vm", cascade="all, delete-orphan"
    )


class MCPServerType(str, enum.Enum):
    """MCP server type enumeration."""

    GITHUB = "github"
    FIGMA = "figma"
    SLACK = "slack"
    NOTION = "notion"
    ATLASSIAN = "atlassian"
    CUSTOM = "custom"


class MCPRequestStatus(str, enum.Enum):
    """MCP request status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class MCPRequest(Base):
    """Log MCP tool invocations for debugging and auditing."""

    __tablename__ = "mcp_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)

    # MCP details
    server_type = Column(SQLEnum(MCPServerType), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False, index=True)
    arguments = Column(JSON, nullable=False, default=dict)

    # Request/Response
    status = Column(
        SQLEnum(MCPRequestStatus),
        nullable=False,
        default=MCPRequestStatus.PENDING,
        index=True,
    )
    response = Column(JSON, nullable=True)  # Tool execution result
    error_message = Column(Text, nullable=True)

    # Performance tracking
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds
    retries = Column(Integer, default=0, nullable=False)

    # Timestamps
    requested_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    session = relationship("Session")


class ComputeUsage(Base):
    """Track compute usage for cost tracking and billing."""

    __tablename__ = "compute_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vm_id = Column(UUID(as_uuid=True), ForeignKey("user_vms.id"), nullable=False)

    # Usage metrics
    start_time = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Calculated on end

    # Resource details
    cpu_type = Column(String(50), nullable=False)  # shared-cpu-1x, performance-cpu-2x
    memory_mb = Column(Integer, nullable=False)
    region = Column(String(50), nullable=True)

    # Cost tracking
    cost_per_hour = Column(Integer, nullable=False)  # In cents (e.g., 27 = $0.0027/hr)
    total_cost_cents = Column(Integer, nullable=True)  # Calculated on end

    # Metadata
    usage_metadata = Column(JSON, nullable=False, default=dict)  # Additional tracking data

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
    user = relationship("User")
    vm = relationship("UserVM", back_populates="compute_usage")


class AgentExecution(Base):
    """Track agent workflow executions."""

    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Execution details
    thread_id = Column(String(255), unique=True, nullable=False, index=True)  # LangGraph thread
    status = Column(
        SQLEnum(AgentExecutionStatus),
        nullable=False,
        default=AgentExecutionStatus.PENDING,
        index=True,
    )

    # Task information
    task_description = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=True)  # code_generation, research, etc.
    subtasks = Column(JSON, nullable=False, default=list)
    completed_subtasks = Column(JSON, nullable=False, default=list)

    # Agent tracking
    agents_involved = Column(JSON, nullable=False, default=list)  # List of agent names
    current_agent = Column(SQLEnum(AgentType), nullable=True)
    agent_statuses = Column(JSON, nullable=False, default=dict)  # agent_name -> status

    # Results
    final_output = Column(Text, nullable=True)
    agent_outputs = Column(JSON, nullable=False, default=list)  # List of agent outputs
    files_changed = Column(JSON, nullable=False, default=list)  # List of file paths

    # Approval tracking
    requires_approval = Column(Boolean, default=False, nullable=False)
    approval_requests = Column(JSON, nullable=False, default=list)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Performance metrics
    total_tokens_used = Column(Integer, default=0, nullable=False)
    total_cost_usd = Column(Integer, default=0, nullable=False)  # In cents
    execution_time_seconds = Column(Integer, nullable=True)

    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
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
    session = relationship("Session")
    user = relationship("User")
    checkpoints = relationship("AgentCheckpoint", back_populates="execution", cascade="all, delete-orphan")


class AgentCheckpoint(Base):
    """Store agent workflow checkpoints for resumption."""

    __tablename__ = "agent_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("agent_executions.id"), nullable=False)

    # Checkpoint details
    checkpoint_id = Column(String(255), unique=True, nullable=False, index=True)
    checkpoint_type = Column(String(50), nullable=False)  # approval, error, completion
    agent_name = Column(SQLEnum(AgentType), nullable=True)

    # State snapshot
    state_data = Column(JSON, nullable=False)  # Serialized AgentState
    checkpoint_metadata = Column(JSON, nullable=False, default=dict)

    # Resumption info
    can_resume = Column(Boolean, default=True, nullable=False)
    resumed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    # Relationships
    execution = relationship("AgentExecution", back_populates="checkpoints")