"""
Main LangGraph workflow assembly.

Combines all agents, tools, and control flow into a compiled graph.
"""

import logging
from typing import Dict, Any, Optional, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import SystemMessage

from app.agents.state import AgentState
from app.agents.supervisor import (
    supervisor_node,
    parallel_executor_node,
    result_aggregator_node,
    error_handler_node,
)
from app.agents.specialists.researcher import researcher_node
from app.agents.specialists.coder import coder_node
from app.agents.specialists.reviewer import reviewer_node
from app.agents.specialists.designer import designer_node
from app.agents.approval import approval_node
from app.agents.persistence import get_checkpoint_manager

logger = logging.getLogger(__name__)


class AgentGraphBuilder:
    """
    Builds and configures the LangGraph multi-agent workflow.

    Handles graph construction, edge routing, and compilation.
    """

    def __init__(self, enable_checkpointing: bool = True):
        """
        Initialize graph builder.

        Args:
            enable_checkpointing: Whether to enable state persistence
        """
        self.enable_checkpointing = enable_checkpointing
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    def build_graph(self) -> StateGraph:
        """
        Build the multi-agent graph structure.

        Returns:
            Constructed StateGraph
        """
        logger.info("Building multi-agent graph")

        # Initialize graph with state schema
        graph = StateGraph(AgentState)

        # Add supervisor and control nodes
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("parallel_executor", parallel_executor_node)
        graph.add_node("result_aggregator", result_aggregator_node)
        graph.add_node("error_handler", error_handler_node)

        # Add specialist agent nodes
        graph.add_node("researcher", researcher_node)
        graph.add_node("coder", coder_node)
        graph.add_node("reviewer", reviewer_node)
        graph.add_node("designer", designer_node)

        # Add approval node
        graph.add_node("approval", approval_node)

        # Define entry point
        graph.add_edge(START, "supervisor")

        # Add conditional edges based on Command routing
        # These edges are determined dynamically by Command.goto

        # Supervisor can route to any specialist or parallel executor
        graph.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "researcher": "researcher",
                "coder": "coder",
                "reviewer": "reviewer",
                "designer": "designer",
                "parallel_executor": "parallel_executor",
                "approval": "approval",
                "error_handler": "error_handler",
                "end": END,
            }
        )

        # Specialists can route to reviewer, approval, or back to aggregator
        for specialist in ["researcher", "coder", "designer"]:
            graph.add_conditional_edges(
                specialist,
                self._route_from_specialist,
                {
                    "reviewer": "reviewer",
                    "approval": "approval",
                    "result_aggregator": "result_aggregator",
                    "error_handler": "error_handler",
                    "end": END,
                }
            )

        # Reviewer routes to approval or end
        graph.add_conditional_edges(
            "reviewer",
            self._route_from_reviewer,
            {
                "approval": "approval",
                "result_aggregator": "result_aggregator",
                "error_handler": "error_handler",
                "end": END,
            }
        )

        # Parallel executor outputs are collected by aggregator
        graph.add_edge("parallel_executor", "result_aggregator")

        # Result aggregator decides next step
        graph.add_conditional_edges(
            "result_aggregator",
            self._route_from_aggregator,
            {
                "approval": "approval",
                "error_handler": "error_handler",
                "end": END,
            }
        )

        # Approval node routes based on approval result
        graph.add_conditional_edges(
            "approval",
            self._route_from_approval,
            {
                "supervisor": "supervisor",  # Retry with modifications
                "coder": "coder",  # Execute approved changes
                "end": END,
            }
        )

        # Error handler can retry or end
        graph.add_conditional_edges(
            "error_handler",
            self._route_from_error_handler,
            {
                "supervisor": "supervisor",  # Retry
                "end": END,
            }
        )

        self.graph = graph
        return graph

    def compile(self, checkpointer: Optional[PostgresSaver] = None) -> Any:
        """
        Compile the graph with optional checkpointing.

        Args:
            checkpointer: Optional PostgresSaver for state persistence

        Returns:
            Compiled graph ready for execution
        """
        if not self.graph:
            self.build_graph()

        # Get checkpointer if enabled
        if self.enable_checkpointing and not checkpointer:
            checkpoint_manager = get_checkpoint_manager()
            checkpointer = checkpoint_manager.get_checkpointer()

        # Compile graph
        self.compiled_graph = self.graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["approval"] if self.enable_checkpointing else None,
        )

        logger.info("Graph compiled successfully")
        return self.compiled_graph

    # Routing functions for conditional edges
    def _route_from_supervisor(self, state: AgentState) -> str:
        """Route from supervisor based on task analysis."""
        current_agent = state.get("current_agent")
        if current_agent:
            return current_agent
        return "end"

    def _route_from_specialist(self, state: AgentState) -> str:
        """Route from specialist agents."""
        if state.get("requires_approval"):
            return "approval"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("subtasks"):
            return "result_aggregator"
        return "end"

    def _route_from_reviewer(self, state: AgentState) -> str:
        """Route from reviewer based on review results."""
        review_comments = state.get("review_comments", [])
        security_issues = state.get("security_issues", [])

        # Check for critical issues
        has_critical = any(
            issue.get("severity") == "CRITICAL"
            for issue in security_issues
        )

        if has_critical or state.get("requires_approval"):
            return "approval"
        elif state.get("subtasks"):
            return "result_aggregator"
        return "end"

    def _route_from_aggregator(self, state: AgentState) -> str:
        """Route from result aggregator."""
        if state.get("requires_approval"):
            return "approval"
        elif state.get("errors"):
            return "error_handler"
        return "end"

    def _route_from_approval(self, state: AgentState) -> str:
        """Route from approval based on user decision."""
        approval_requests = state.get("approval_requests", [])
        if approval_requests:
            latest_approval = approval_requests[-1]
            if latest_approval.get("approved"):
                # Approved - continue with operation
                if state.get("pending_changes"):
                    return "coder"  # Execute code changes
                return "supervisor"  # Re-analyze with approval
        return "end"

    def _route_from_error_handler(self, state: AgentState) -> str:
        """Route from error handler based on retry logic."""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if retry_count < max_retries:
            return "supervisor"  # Retry
        return "end"


def create_agent_graph(
    enable_checkpointing: bool = True,
    checkpointer: Optional[PostgresSaver] = None,
) -> Any:
    """
    Create and compile the multi-agent graph.

    Args:
        enable_checkpointing: Whether to enable state persistence
        checkpointer: Optional custom checkpointer

    Returns:
        Compiled graph ready for execution
    """
    builder = AgentGraphBuilder(enable_checkpointing)
    return builder.compile(checkpointer)


async def execute_agent_workflow(
    messages: list,
    session_id: str,
    user_id: str,
    config: Optional[Dict[str, Any]] = None,
    stream_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Execute the agent workflow with given input.

    Args:
        messages: Input messages to process
        session_id: Session identifier
        user_id: User identifier
        config: Optional LangGraph configuration
        stream_callback: Optional callback for streaming updates

    Returns:
        Final state after workflow execution
    """
    # Create or get compiled graph
    graph = create_agent_graph()

    # Prepare initial state
    initial_state = {
        "messages": messages,
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.now(),
        "agent_statuses": {},
        "agent_outputs": [],
        "errors": [],
        "retry_count": 0,
        "max_retries": 3,
        "total_tokens_used": 0,
        "total_cost_usd": 0.0,
    }

    # Prepare configuration
    if not config:
        checkpoint_manager = get_checkpoint_manager()
        config = checkpoint_manager.get_thread_config(
            thread_id=session_id,
            metadata={
                "user_id": user_id,
                "started_at": datetime.now().isoformat(),
            }
        )

    try:
        # Execute graph
        if stream_callback:
            # Stream execution with callbacks
            final_state = None
            async for event in graph.astream(initial_state, config):
                # Send streaming update
                await stream_callback(event)
                final_state = event
            return final_state
        else:
            # Batch execution
            final_state = await graph.ainvoke(initial_state, config)
            return final_state

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise


# Export key components
__all__ = [
    "create_agent_graph",
    "execute_agent_workflow",
    "AgentGraphBuilder",
]