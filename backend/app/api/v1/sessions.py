"""
Session management endpoints.
"""
from typing import List, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field, validator, HttpUrl
from datetime import datetime

from app.db.database import AsyncSession, get_session
from app.db.models import User, SessionStatus, MessageRole
from app.core.auth import get_current_active_user
from app.services.session_service import SessionService
from app.core.exceptions import NotFoundError, SessionError

router = APIRouter()


# Request/Response models
class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    repo_url: Optional[str] = Field(None, description="Repository URL", max_length=500)
    branch_name: Optional[str] = Field(None, description="Git branch name", max_length=255)
    project_name: Optional[str] = Field(None, description="Project name", max_length=255)
    description: Optional[str] = Field(None, description="Session description", max_length=1000)

    @validator('branch_name')
    def validate_branch(cls, v):
        """Validate branch name for path traversal and invalid characters."""
        if v and ('../' in v or '\0' in v or v.startswith('/')):
            raise ValueError('Invalid branch name: path traversal detected')
        return v

    @validator('repo_url', pre=True)
    def validate_repo_url(cls, v):
        """Validate repository URL length and format."""
        if v and len(str(v)) > 500:
            raise ValueError('URL too long')
        return v


class SyncSessionRequest(BaseModel):
    """Request model for syncing from desktop."""

    desktop_session_id: str = Field(..., description="Desktop session identifier", max_length=255)
    repo_url: Optional[str] = Field(None, description="Repository URL", max_length=500)
    branch_name: Optional[str] = Field(None, description="Git branch name", max_length=255)
    project_name: Optional[str] = Field(None, description="Project name", max_length=255)
    commit_sha: Optional[str] = Field(None, description="Current commit SHA", max_length=40)
    files_changed: Optional[List[str]] = Field(default_factory=list, description="Changed files")
    messages: Optional[List[dict]] = Field(default_factory=list, description="Conversation history")

    @validator('branch_name')
    def validate_branch(cls, v):
        """Validate branch name for path traversal and invalid characters."""
        if v and ('../' in v or '\0' in v or v.startswith('/')):
            raise ValueError('Invalid branch name: path traversal detected')
        return v

    @validator('repo_url', pre=True)
    def validate_repo_url(cls, v):
        """Validate repository URL length and format."""
        if v and len(str(v)) > 500:
            raise ValueError('URL too long')
        return v

    @validator('commit_sha')
    def validate_commit_sha(cls, v):
        """Validate commit SHA format."""
        if v and (len(v) != 40 or not all(c in '0123456789abcdef' for c in v.lower())):
            raise ValueError('Invalid commit SHA format')
        return v


class SessionResponse(BaseModel):
    """Response model for session data."""

    id: UUID
    user_id: UUID
    status: SessionStatus
    repo_url: Optional[str]
    branch_name: Optional[str]
    project_name: Optional[str]
    description: Optional[str]
    desktop_session_id: Optional[str]
    current_agent: Optional[str]
    agent_statuses: dict
    langgraph_thread_id: Optional[str]
    vm_machine_id: Optional[str]
    vm_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for message data."""

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    voice_transcript: Optional[str]
    agent: Optional[str]
    metadata: dict
    timestamp: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Create a new coding session.
    """
    service = SessionService(db)
    session = await service.create_session(
        user=current_user,
        repo_url=request.repo_url,
        branch_name=request.branch_name,
        project_name=request.project_name,
        description=request.description,
    )
    return SessionResponse.model_validate(session)


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip results"),
):
    """
    List user's sessions.
    """
    service = SessionService(db)
    sessions = await service.list_user_sessions(
        user=current_user,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Get session details.
    """
    service = SessionService(db)
    session = await service.get_session(session_id, current_user)
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    End and delete a session.
    """
    service = SessionService(db)
    await service.delete_session(session_id, current_user)
    return None


@router.post("/{session_id}/sync", response_model=SessionResponse)
async def sync_session(
    request: SyncSessionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Sync session from desktop (Claude Code, Cursor, etc).
    """
    service = SessionService(db)

    context = {
        "repo_url": request.repo_url,
        "branch_name": request.branch_name,
        "project_name": request.project_name,
        "commit_sha": request.commit_sha,
        "files_changed": request.files_changed,
        "messages": request.messages,
    }

    session = await service.sync_from_desktop(
        user=current_user,
        desktop_session_id=request.desktop_session_id,
        context=context,
    )
    return SessionResponse.model_validate(session)


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(50, ge=1, le=200, description="Maximum messages"),
    offset: int = Query(0, ge=0, description="Skip messages"),
):
    """
    Get messages for a session.
    """
    service = SessionService(db)
    messages = await service.get_session_messages(
        session_id=session_id,
        user=current_user,
        limit=limit,
        offset=offset,
    )
    return [MessageResponse.model_validate(m) for m in messages]