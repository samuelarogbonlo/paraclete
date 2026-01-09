"""
Agent invocation and management endpoints with LangGraph integration.
"""
from typing import Optional, Dict, Any, Annotated, List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import logging
import json

from sqlalchemy import select
from langchain_core.messages import HumanMessage, AIMessage

from app.db.database import AsyncSession, get_session
from app.db.models import (
    User, MessageRole, AgentExecution,
    AgentExecutionStatus, AgentCheckpoint, AgentType
)
from app.core.auth import get_current_active_user
from app.services.session_service import SessionService
from app.core.exceptions import NotFoundError, SessionError

# Import agent components
from app.agents.graph import execute_agent_workflow
from app.agents.approval import get_approval_manager
from app.agents.persistence import get_checkpoint_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class InvokeAgentRequest(BaseModel):
    """Request model for invoking agent."""

    input_text: Optional[str] = Field(None, description="Text input")
    voice_transcript: Optional[str] = Field(None, description="Voice transcript")
    agent_type: Optional[str] = Field(None, description="Specific agent to invoke")
    require_approval: bool = Field(False, description="Require approval for actions")


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""

    agent: str
    status: str  # pending, running, complete, error, awaiting_approval
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    message: Optional[str]
    error: Optional[str]


class ApprovalRequest(BaseModel):
    """Request model for approval."""

    approved: bool = Field(..., description="Whether to approve the action")
    feedback: Optional[str] = Field(None, description="Optional feedback")


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""

    session_id: UUID
    message: str
    agent_statuses: Dict[str, str]
    requires_approval: bool = False
    approval_action_id: Optional[str] = None


@router.post("/{session_id}/invoke", response_model=InvokeResponse)
async def invoke_agent(
    session_id: UUID,
    request: InvokeAgentRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Invoke AI agent with voice or text input.

    This endpoint:
    1. Sends input to LangGraph supervisor
    2. Routes to appropriate specialist agents
    3. Streams results via WebSocket
    4. Handles human-in-the-loop approval
    """
    service = SessionService(db)

    # Verify session exists and user has access
    session = await service.get_session(session_id, current_user)

    # Add user message to session
    input_content = request.voice_transcript or request.input_text or ""
    await service.add_message(
        session_id=session_id,
        user=current_user,
        role=MessageRole.USER,
        content=input_content,
        voice_transcript=request.voice_transcript,
    )

    # Create agent execution record
    thread_id = f"thread_{session_id}_{uuid4().hex[:8]}"
    execution = AgentExecution(
        session_id=session_id,
        user_id=current_user.id,
        thread_id=thread_id,
        status=AgentExecutionStatus.PENDING,
        task_description=input_content,
        requires_approval=request.require_approval,
        agents_involved=[],
        agent_statuses={},
    )
    db.add(execution)
    await db.commit()

    # Execute LangGraph workflow in background
    async def execute_workflow():
        try:
            # Prepare messages for LangGraph
            messages = [HumanMessage(content=input_content)]

            # Get user's API keys if BYOK
            user_api_keys = None
            # TODO: Fetch encrypted API keys and decrypt

            # Execute workflow
            final_state = await execute_agent_workflow(
                messages=messages,
                session_id=str(session_id),
                user_id=str(current_user.id),
                config={
                    "configurable": {
                        "thread_id": thread_id,
                    },
                    "metadata": {
                        "execution_id": str(execution.id),
                        "agent_type": request.agent_type,
                    }
                },
                stream_callback=None,  # WebSocket streaming handled separately
            )

            # Update execution record with results
            execution.status = AgentExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.final_output = final_state.get("messages", [])[-1].content if final_state.get("messages") else ""
            execution.agent_outputs = final_state.get("agent_outputs", [])
            execution.files_changed = final_state.get("files_changed", [])
            execution.total_tokens_used = final_state.get("total_tokens_used", 0)
            execution.total_cost_usd = int(final_state.get("total_cost_usd", 0) * 100)  # Convert to cents

            await db.commit()

            # Add final message to session
            if final_state.get("messages"):
                final_message = final_state["messages"][-1]
                await service.add_message(
                    session_id=session_id,
                    user=current_user,
                    role=MessageRole.ASSISTANT,
                    content=final_message.content if hasattr(final_message, 'content') else str(final_message),
                    agent="supervisor",
                    metadata={"execution_id": str(execution.id)},
                )

        except Exception as e:
            logger.error(f"Agent workflow failed: {e}")
            execution.status = AgentExecutionStatus.FAILED
            execution.last_error = str(e)
            execution.error_count += 1
            await db.commit()

    background_tasks.add_task(execute_workflow)

    # Initial agent statuses
    initial_statuses = {
        "supervisor": "running",
        "researcher": "pending",
        "coder": "pending",
        "reviewer": "pending",
        "designer": "pending",
    }

    return InvokeResponse(
        session_id=session_id,
        message="Agent workflow started. Results will be streamed via WebSocket.",
        agent_statuses=initial_statuses,
        requires_approval=request.require_approval,
        approval_action_id=thread_id if request.require_approval else None,
    )


@router.get("/{session_id}/agents", response_model=Dict[str, AgentStatusResponse])
async def get_agent_statuses(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Get current status of all agents in session.
    """
    service = SessionService(db)
    session = await service.get_session(session_id, current_user)

    # TODO: Phase 2 - Get actual agent statuses from LangGraph
    # For now, return placeholder statuses

    statuses = {}
    for agent_name, status in session.agent_statuses.items():
        statuses[agent_name] = AgentStatusResponse(
            agent=agent_name,
            status=status,
            started_at=datetime.utcnow() if status == "running" else None,
            completed_at=datetime.utcnow() if status == "complete" else None,
            message=f"{agent_name} is {status}",
            error=None,
        )

    return statuses


@router.post("/{session_id}/approve", status_code=status.HTTP_200_OK)
async def approve_action(
    session_id: UUID,
    request: ApprovalRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Approve or reject a pending agent action.

    This handles human-in-the-loop approval for sensitive operations
    like code changes, git pushes, or file deletions.
    """
    service = SessionService(db)
    session = await service.get_session(session_id, current_user)

    # Find the active execution for this session
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.session_id == session_id)
        .where(AgentExecution.status == AgentExecutionStatus.INTERRUPTED)
        .order_by(AgentExecution.created_at.desc())
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending approval found for this session"
        )

    # Get approval manager
    approval_manager = get_approval_manager()

    # Process approval
    success = await approval_manager.process_approval_response(
        request_id=execution.thread_id,  # Using thread_id as approval ID
        approved=request.approved,
        approved_by=str(current_user.id),
        feedback=request.feedback,
    )

    if success:
        # Update execution record
        execution.status = (
            AgentExecutionStatus.APPROVED if request.approved
            else AgentExecutionStatus.REJECTED
        )
        execution.approved_by = str(current_user.id)
        execution.approved_at = datetime.utcnow()
        await db.commit()

        # Resume workflow if approved
        if request.approved:
            # The workflow will automatically resume from checkpoint
            logger.info(f"Resuming workflow {execution.thread_id} after approval")

    # Add approval message to session
    await service.add_message(
        session_id=session_id,
        user=current_user,
        role=MessageRole.USER,
        content=f"{'Approved' if request.approved else 'Rejected'}: {request.feedback or 'No feedback'}",
        metadata={"type": "approval", "approved": request.approved},
    )

    return {
        "message": f"Action {'approved' if request.approved else 'rejected'}",
        "session_id": session_id,
        "execution_id": str(execution.id),
    }


@router.post("/{session_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_task(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Cancel the current agent task.
    """
    service = SessionService(db)
    session = await service.get_session(session_id, current_user)

    # Find active execution
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.session_id == session_id)
        .where(AgentExecution.status.in_([
            AgentExecutionStatus.PENDING,
            AgentExecutionStatus.RUNNING,
            AgentExecutionStatus.INTERRUPTED
        ]))
    )
    execution = result.scalar_one_or_none()

    if execution:
        # Cancel execution
        execution.status = AgentExecutionStatus.FAILED
        execution.last_error = "Cancelled by user"
        execution.completed_at = datetime.utcnow()
        await db.commit()

    # Update session status
    await service.update_session(
        session_id=session_id,
        user=current_user,
        updates={
            "agent_statuses": {
                agent: "cancelled" for agent in session.agent_statuses
            },
            "current_agent": None,
        },
    )

    return {
        "message": "Agent task cancelled",
        "session_id": session_id,
        "execution_id": str(execution.id) if execution else None,
    }


@router.get("/{session_id}/executions", response_model=List[Dict[str, Any]])
async def get_executions(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 10,
):
    """
    Get agent execution history for a session.
    """
    service = SessionService(db)
    await service.get_session(session_id, current_user)  # Verify access

    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.session_id == session_id)
        .order_by(AgentExecution.created_at.desc())
        .limit(limit)
    )
    executions = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "thread_id": e.thread_id,
            "status": e.status.value,
            "task_description": e.task_description,
            "task_type": e.task_type,
            "agents_involved": e.agents_involved,
            "final_output": e.final_output,
            "files_changed": e.files_changed,
            "total_tokens_used": e.total_tokens_used,
            "total_cost_cents": e.total_cost_usd,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "error": e.last_error,
        }
        for e in executions
    ]


@router.get("/execution/{execution_id}", response_model=Dict[str, Any])
async def get_execution_details(
    execution_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Get detailed information about a specific agent execution.
    """
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.id == execution_id)
        .where(AgentExecution.user_id == current_user.id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )

    # Get checkpoints
    checkpoint_result = await db.execute(
        select(AgentCheckpoint)
        .where(AgentCheckpoint.execution_id == execution_id)
        .order_by(AgentCheckpoint.created_at.desc())
    )
    checkpoints = checkpoint_result.scalars().all()

    return {
        "id": str(execution.id),
        "session_id": str(execution.session_id),
        "thread_id": execution.thread_id,
        "status": execution.status.value,
        "task_description": execution.task_description,
        "task_type": execution.task_type,
        "subtasks": execution.subtasks,
        "completed_subtasks": execution.completed_subtasks,
        "agents_involved": execution.agents_involved,
        "current_agent": execution.current_agent.value if execution.current_agent else None,
        "agent_statuses": execution.agent_statuses,
        "agent_outputs": execution.agent_outputs,
        "final_output": execution.final_output,
        "files_changed": execution.files_changed,
        "requires_approval": execution.requires_approval,
        "approval_requests": execution.approval_requests,
        "approved_by": execution.approved_by,
        "approved_at": execution.approved_at.isoformat() if execution.approved_at else None,
        "total_tokens_used": execution.total_tokens_used,
        "total_cost_cents": execution.total_cost_usd,
        "execution_time_seconds": execution.execution_time_seconds,
        "error_count": execution.error_count,
        "last_error": execution.last_error,
        "started_at": execution.started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "checkpoints": [
            {
                "id": str(c.id),
                "checkpoint_id": c.checkpoint_id,
                "type": c.checkpoint_type,
                "agent": c.agent_name.value if c.agent_name else None,
                "can_resume": c.can_resume,
                "created_at": c.created_at.isoformat(),
            }
            for c in checkpoints
        ],
    }