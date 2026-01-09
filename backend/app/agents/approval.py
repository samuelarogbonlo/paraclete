"""
Human-in-the-loop approval workflow for sensitive operations.

Implements checkpoint-based interrupts for human review and approval.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command, interrupt
from langgraph.constants import Send

from app.agents.state import AgentState, ApprovalRequest, GitChange

logger = logging.getLogger(__name__)


class ApprovalType:
    """Types of operations requiring approval."""

    GIT_PUSH = "git_push"
    FILE_WRITE = "file_write"
    COMMAND_EXECUTION = "command_execution"
    API_CALL = "api_call"
    DEPLOYMENT = "deployment"
    DATABASE_CHANGE = "database_change"


class ApprovalManager:
    """
    Manages approval requests and responses.

    Handles WebSocket notifications and approval state tracking.
    """

    def __init__(self):
        """Initialize approval manager."""
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_callbacks: Dict[str, asyncio.Future] = {}

    async def request_approval(
        self,
        request_type: str,
        description: str,
        details: Dict[str, Any],
        session_id: str,
        user_id: str,
    ) -> str:
        """
        Create an approval request.

        Args:
            request_type: Type of approval needed
            description: Human-readable description
            details: Additional context for approval
            session_id: Current session ID
            user_id: User who needs to approve

        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())

        approval_request = ApprovalRequest(
            request_id=request_id,
            type=request_type,
            description=description,
            details=details,
            requested_at=datetime.now(),
            approved=None,
            approved_by=None,
            approved_at=None,
        )

        self.pending_approvals[request_id] = approval_request

        # Create a future for async waiting
        future = asyncio.Future()
        self.approval_callbacks[request_id] = future

        # Send WebSocket notification (would be implemented in websocket module)
        await self._notify_approval_request(
            request_id,
            session_id,
            user_id,
            approval_request,
        )

        return request_id

    async def process_approval_response(
        self,
        request_id: str,
        approved: bool,
        approved_by: str,
        feedback: Optional[str] = None,
    ) -> bool:
        """
        Process an approval response from the user.

        Args:
            request_id: The approval request ID
            approved: Whether approved or rejected
            approved_by: User who approved/rejected
            feedback: Optional feedback from user

        Returns:
            True if processed successfully
        """
        if request_id not in self.pending_approvals:
            logger.warning(f"Approval request {request_id} not found")
            return False

        # Update approval request
        approval = self.pending_approvals[request_id]
        approval["approved"] = approved
        approval["approved_by"] = approved_by
        approval["approved_at"] = datetime.now()

        if feedback:
            approval["details"]["feedback"] = feedback

        # Resolve the future
        if request_id in self.approval_callbacks:
            future = self.approval_callbacks[request_id]
            if not future.done():
                future.set_result(approval)

        # Clean up if rejected
        if not approved:
            del self.pending_approvals[request_id]
            del self.approval_callbacks[request_id]

        return True

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[int] = None,
    ) -> Optional[ApprovalRequest]:
        """
        Wait for approval response.

        Args:
            request_id: The approval request ID
            timeout: Optional timeout in seconds

        Returns:
            Approved request or None if timeout/rejected
        """
        if request_id not in self.approval_callbacks:
            logger.error(f"No callback registered for request {request_id}")
            return None

        future = self.approval_callbacks[request_id]

        try:
            if timeout:
                result = await asyncio.wait_for(future, timeout=timeout)
            else:
                result = await future

            return result if result.get("approved") else None

        except asyncio.TimeoutError:
            logger.warning(f"Approval request {request_id} timed out")
            return None

        finally:
            # Clean up
            if request_id in self.approval_callbacks:
                del self.approval_callbacks[request_id]

    async def _notify_approval_request(
        self,
        request_id: str,
        session_id: str,
        user_id: str,
        approval_request: ApprovalRequest,
    ):
        """Send WebSocket notification for approval request."""
        # This would integrate with websocket.py to send real-time notification
        logger.info(f"Approval requested: {request_id} for session {session_id}")
        # Implementation would send WebSocket message to connected client


# Global approval manager instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get global approval manager instance."""
    global _approval_manager
    if not _approval_manager:
        _approval_manager = ApprovalManager()
    return _approval_manager


def approval_node(state: AgentState) -> Command:
    """
    Approval node that interrupts workflow for human review.

    This node creates a checkpoint and waits for human approval
    before proceeding with sensitive operations.
    """
    logger.info(f"Approval node activated for session {state['session_id']}")

    # Check what needs approval
    pending_changes = state.get("pending_changes", [])
    requires_approval = state.get("requires_approval", False)

    if not requires_approval and not pending_changes:
        logger.info("No approval needed, continuing workflow")
        return Command(
            goto="END",
            update={"requires_approval": False}
        )

    # Determine approval type and prepare details
    approval_type, description, details = prepare_approval_request(state)

    # Create approval request
    request_id = str(uuid.uuid4())
    approval_request = ApprovalRequest(
        request_id=request_id,
        type=approval_type,
        description=description,
        details=details,
        requested_at=datetime.now(),
        approved=None,
        approved_by=None,
        approved_at=None,
    )

    # Generate approval message for user
    approval_message = generate_approval_message(approval_request, state)

    # Update state with approval request
    state_update = {
        "approval_requests": state.get("approval_requests", []) + [approval_request],
        "approval_checkpoint_id": request_id,
        "interrupt_reason": "Awaiting human approval",
        "messages": [AIMessage(
            content=approval_message,
            metadata={
                "agent": "approval",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "requires_action": True,
            }
        )],
    }

    # Use LangGraph's interrupt to pause execution
    # The workflow will resume when approval is received
    interrupt(value=approval_request)

    # This code runs after interrupt is resumed
    # Check if approved
    if approval_request.get("approved"):
        logger.info(f"Approval granted for request {request_id}")

        # Continue based on what was approved
        if approval_type == ApprovalType.GIT_PUSH:
            next_node = "git_executor"  # Execute git operations
        elif approval_type == ApprovalType.FILE_WRITE:
            next_node = "file_executor"  # Execute file operations
        else:
            next_node = "END"

        state_update["requires_approval"] = False
        state_update["messages"].append(
            HumanMessage(content=f"Approved: {approval_request.get('feedback', 'Proceeding with operation')}")
        )

    else:
        logger.info(f"Approval rejected for request {request_id}")
        next_node = "END"
        state_update["requires_approval"] = False
        state_update["messages"].append(
            HumanMessage(content=f"Rejected: {approval_request.get('feedback', 'Operation cancelled')}")
        )

    return Command(
        goto=next_node,
        update=state_update,
    )


def prepare_approval_request(state: AgentState) -> tuple[str, str, Dict[str, Any]]:
    """
    Prepare approval request based on state.

    Returns:
        Tuple of (approval_type, description, details)
    """
    pending_changes = state.get("pending_changes", [])
    agent_outputs = state.get("agent_outputs", [])

    # Check for git operations
    if pending_changes:
        file_list = [change["file_path"] for change in pending_changes]
        return (
            ApprovalType.GIT_PUSH,
            f"Approve changes to {len(pending_changes)} files",
            {
                "files": file_list,
                "changes": pending_changes,
                "branch": state.get("branch_name", "main"),
                "repo": state.get("repo_url"),
            }
        )

    # Check for critical issues from reviewer
    for output in agent_outputs:
        if output.get("agent_name") == "reviewer":
            result = output.get("result", {})
            review = result.get("review", {})
            if review.get("has_critical_issues"):
                return (
                    ApprovalType.COMMAND_EXECUTION,
                    "Critical issues found in code review",
                    {
                        "security_issues": review.get("security_issues", []),
                        "performance_issues": review.get("performance_issues", []),
                        "recommendation": "Fix critical issues before proceeding",
                    }
                )

    # Default approval
    return (
        ApprovalType.COMMAND_EXECUTION,
        "Approve workflow continuation",
        {
            "task": state.get("task_description", ""),
            "completed_steps": len(state.get("completed_subtasks", [])),
            "remaining_steps": len(state.get("subtasks", [])) - len(state.get("completed_subtasks", [])),
        }
    )


def generate_approval_message(approval_request: ApprovalRequest, state: AgentState) -> str:
    """Generate human-readable approval message."""
    messages = ["## Approval Required\n"]

    request_type = approval_request["type"]
    details = approval_request["details"]

    if request_type == ApprovalType.GIT_PUSH:
        messages.append("### Git Changes")
        messages.append(f"**Branch:** {details.get('branch', 'main')}")
        messages.append(f"**Repository:** {details.get('repo', 'Not specified')}")
        messages.append(f"\n**Files to be modified ({len(details.get('files', []))}):**")
        for file_path in details.get("files", [])[:10]:  # Show first 10 files
            messages.append(f"- {file_path}")
        if len(details.get("files", [])) > 10:
            messages.append(f"- ... and {len(details['files']) - 10} more files")

    elif request_type == ApprovalType.FILE_WRITE:
        messages.append("### File Operations")
        messages.append(f"**Files to write:** {len(details.get('files', []))}")

    elif request_type == ApprovalType.COMMAND_EXECUTION:
        if details.get("security_issues"):
            messages.append("### \u26a0\ufe0f Security Issues Found")
            for issue in details["security_issues"][:3]:
                messages.append(f"- [{issue['severity']}] {issue['description']}")

        if details.get("recommendation"):
            messages.append(f"\n**Recommendation:** {details['recommendation']}")

    messages.append("\n**Action Required:** Please review and approve or reject this operation.")
    messages.append("- To approve: POST /v1/agents/{agent_id}/approve with {\"approved\": true}")
    messages.append("- To reject: POST /v1/agents/{agent_id}/approve with {\"approved\": false}")

    return "\n".join(messages)