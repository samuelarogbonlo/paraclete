"""
LangGraph multi-agent orchestration system for Paraclete.

This module implements a sophisticated AI agent workflow using:
- LangGraph for orchestration with Command and Send APIs
- Multiple specialist agents (researcher, coder, reviewer, designer)
- PostgresSaver for state persistence and checkpointing
- Human-in-the-loop approval workflows
- Intelligent model routing for cost optimization

Architecture:
1. Supervisor agent analyzes tasks and routes to specialists
2. Specialist agents execute with appropriate models
3. Parallel execution for independent subtasks
4. Approval checkpoints for sensitive operations
5. State persistence enables workflow resumption
"""

from app.agents.graph import create_agent_graph, execute_agent_workflow
from app.agents.state import AgentState, AgentOutput, ApprovalRequest
from app.agents.router import ModelRouter, AgentType
from app.agents.persistence import get_checkpoint_manager, initialize_persistence
from app.agents.approval import get_approval_manager

__all__ = [
    "create_agent_graph",
    "execute_agent_workflow",
    "AgentState",
    "AgentOutput",
    "ApprovalRequest",
    "ModelRouter",
    "AgentType",
    "get_checkpoint_manager",
    "get_approval_manager",
    "initialize_persistence",
]

# Version info
__version__ = "1.0.0"