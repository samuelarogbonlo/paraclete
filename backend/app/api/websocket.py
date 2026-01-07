"""
WebSocket handlers for real-time streaming.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, ValidationError
import json
import asyncio
import logging
from datetime import datetime

from app.db.database import AsyncSession, get_session as get_db_session
from app.db.models import User
from app.services.session_service import SessionService
from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, WebSocketError

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""

    type: str
    timestamp: datetime = datetime.utcnow()


class VoiceInputMessage(WebSocketMessage):
    """Voice input message from client."""

    type: str = "voice_input"
    transcript: str


class ApprovalMessage(WebSocketMessage):
    """Approval message from client."""

    type: str = "approval"
    action_id: str
    approved: bool


class CancelMessage(WebSocketMessage):
    """Cancel message from client."""

    type: str = "cancel"
    reason: Optional[str] = None


class AgentStatusMessage(WebSocketMessage):
    """Agent status message to client."""

    type: str = "agent_status"
    agent: str
    status: str
    message: Optional[str] = None


class AgentOutputMessage(WebSocketMessage):
    """Agent output message to client."""

    type: str = "agent_output"
    agent: str
    content: str
    streaming: bool = False


class ApprovalRequiredMessage(WebSocketMessage):
    """Approval required message to client."""

    type: str = "approval_required"
    action_id: str
    action_type: str
    description: str
    details: Dict[str, Any] = {}


class SessionUpdateMessage(WebSocketMessage):
    """Session update message to client."""

    type: str = "session_update"
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    files_changed: list = []


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Accept and track a new connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")

    def disconnect(self, session_id: str, user_id: str):
        """Remove a disconnected client."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        logger.info(f"WebSocket disconnected: session={session_id}, user={user_id}")

    async def send_message(self, session_id: str, message: WebSocketMessage):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message.dict())
                except Exception as e:
                    logger.error(f"Error sending message to {session_id}: {e}")

    async def broadcast_to_user(self, user_id: str, message: WebSocketMessage):
        """Broadcast a message to all of a user's sessions."""
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            await self.send_message(session_id, message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(..., description="Session ID to stream"),
):
    """
    WebSocket endpoint for real-time agent streaming.

    Authentication is done via first message after connection (auth message).
    This prevents token exposure in query parameters and logs.

    Query parameters:
    - session_id: Session ID to connect to

    Message types (client -> server):
    - auth: Authentication message (must be first, contains JWT token)
    - voice_input: Voice transcription input
    - approval: Approval/rejection of agent action
    - cancel: Cancel current task

    Message types (server -> client):
    - agent_status: Agent status update
    - agent_output: Agent output/response
    - approval_required: Request for human approval
    - session_update: Session state update
    """
    user = None
    session = None
    db: Optional[AsyncSession] = None

    try:
        # Accept connection first
        await websocket.accept()

        # Wait for authentication message (5 second timeout)
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=5.0
            )

            if auth_data.get('type') != 'auth':
                await websocket.close(code=1008, reason="Auth message required as first message")
                return

            token = auth_data.get('data', {}).get('token')
            if not token:
                await websocket.close(code=1008, reason="Token missing in auth message")
                return

            # Authenticate user from token
            token_data = decode_token(token)
            user_id = token_data.sub

        except asyncio.TimeoutError:
            logger.error("WebSocket auth timeout")
            await websocket.close(code=1008, reason="Auth timeout")
            return
        except Exception as e:
            logger.error(f"WebSocket auth error: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return

        # Get database session
        async for db_session in get_db_session():
            db = db_session
            break

        if not db:
            await websocket.close(code=4002, reason="Database error")
            return

        # Verify session exists and user has access
        service = SessionService(db)
        try:
            # Get user from database
            from sqlalchemy import select
            from app.db.models import User

            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                await websocket.close(code=4001, reason="User not found")
                return

            # Get session
            session = await service.get_session(UUID(session_id), user)
        except Exception as e:
            logger.error(f"Session verification error: {e}")
            await websocket.close(code=4003, reason="Session not found or access denied")
            return

        # Accept connection
        await manager.connect(websocket, session_id, str(user.id))

        # Send initial session state
        await manager.send_message(
            session_id,
            SessionUpdateMessage(
                branch=session.branch_name,
                commit_sha=session.current_commit_sha,
                files_changed=session.files_changed or [],
            ),
        )

        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                # Parse message type
                msg_type = data.get("type")

                if msg_type == "voice_input":
                    # Handle voice input
                    message = VoiceInputMessage(**data)
                    await handle_voice_input(session_id, message, service, user)

                elif msg_type == "approval":
                    # Handle approval
                    message = ApprovalMessage(**data)
                    await handle_approval(session_id, message, service, user)

                elif msg_type == "cancel":
                    # Handle cancel
                    message = CancelMessage(**data)
                    await handle_cancel(session_id, message, service, user)

                elif msg_type == "ping":
                    # Handle ping/pong for connection health
                    await websocket.send_json({"type": "pong"})

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

            except ValidationError as e:
                logger.error(f"Message validation error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format",
                    "details": str(e),
                })

            except WebSocketDisconnect:
                break

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal server error",
                })

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    finally:
        # Clean up connection
        if user and session:
            manager.disconnect(session_id, str(user.id))

        # Close database session
        if db:
            await db.close()


async def handle_voice_input(
    session_id: str,
    message: VoiceInputMessage,
    service: SessionService,
    user: User,
):
    """Handle voice input message."""
    # TODO: Phase 2 - Send to LangGraph for processing

    # For now, send placeholder response
    await manager.send_message(
        session_id,
        AgentStatusMessage(
            agent="supervisor",
            status="running",
            message="Processing voice input...",
        ),
    )

    # Simulate agent output
    await asyncio.sleep(1)
    await manager.send_message(
        session_id,
        AgentOutputMessage(
            agent="supervisor",
            content=f"[Placeholder] Received: {message.transcript[:100]}",
            streaming=False,
        ),
    )


async def handle_approval(
    session_id: str,
    message: ApprovalMessage,
    service: SessionService,
    user: User,
):
    """Handle approval message."""
    # TODO: Phase 2 - Send approval to LangGraph

    # Send confirmation
    await manager.send_message(
        session_id,
        AgentStatusMessage(
            agent="supervisor",
            status="running",
            message=f"Action {'approved' if message.approved else 'rejected'}",
        ),
    )


async def handle_cancel(
    session_id: str,
    message: CancelMessage,
    service: SessionService,
    user: User,
):
    """Handle cancel message."""
    # TODO: Phase 2 - Cancel LangGraph execution

    # Send confirmation
    await manager.send_message(
        session_id,
        AgentStatusMessage(
            agent="supervisor",
            status="cancelled",
            message=f"Task cancelled: {message.reason or 'User requested'}",
        ),
    )