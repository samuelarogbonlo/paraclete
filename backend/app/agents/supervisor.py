"""
Supervisor agent with Command API for intelligent task routing.

The supervisor analyzes incoming requests and routes them to appropriate
specialist agents using LangGraph's Command API for control flow.
"""

import re
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import logging

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.types import Command
from langgraph.constants import Send

from app.agents.state import AgentState, ParallelTaskState
from app.agents.router import ModelRouter, AgentType

logger = logging.getLogger(__name__)


class TaskClassifier:
    """Classifies tasks and determines routing strategy."""

    # Task patterns for classification
    TASK_PATTERNS = {
        "code_generation": [
            r"create|implement|build|write.*(?:function|class|component|api|endpoint)",
            r"generate.*code",
            r"add.*feature",
        ],
        "code_review": [
            r"review|check|analyze.*code",
            r"find.*(?:bug|issue|problem)",
            r"security.*(?:audit|check|review)",
            r"performance.*(?:review|analysis)",
        ],
        "research": [
            r"search|find|look.*(?:up|for)",
            r"research|investigate|explore",
            r"documentation|docs.*(?:for|about)",
            r"what.*(?:is|are|does)",
            r"how.*(?:to|does|can)",
        ],
        "design": [
            r"design|architect|plan",
            r"structure|organize",
            r"diagram|flow.*chart",
            r"ui|ux|interface",
        ],
        "debugging": [
            r"debug|fix|solve|resolve",
            r"error|exception|crash",
            r"not.*working|broken|failing",
        ],
        "refactoring": [
            r"refactor|optimize|improve",
            r"clean.*up|reorganize",
            r"performance.*(?:improve|optimize)",
        ],
    }

    @classmethod
    def classify_task(cls, task_description: str) -> str:
        """Classify task based on description patterns."""
        task_lower = task_description.lower()

        for task_type, patterns in cls.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, task_lower):
                    return task_type

        return "general"

    @classmethod
    def identify_subtasks(cls, task_description: str) -> List[str]:
        """Break down complex tasks into subtasks."""
        subtasks = []

        # Look for numbered lists
        numbered_pattern = r"\d+\.\s+([^\n]+)"
        numbered_matches = re.findall(numbered_pattern, task_description)
        if numbered_matches:
            subtasks.extend(numbered_matches)

        # Look for bullet points
        bullet_pattern = r"[-•*]\s+([^\n]+)"
        bullet_matches = re.findall(bullet_pattern, task_description)
        if bullet_matches:
            subtasks.extend(bullet_matches)

        # Look for "and" separated tasks
        if not subtasks and " and " in task_description.lower():
            parts = re.split(r",?\s+and\s+", task_description)
            if len(parts) <= 4:  # Reasonable number of subtasks
                subtasks = parts

        return subtasks

    @classmethod
    def can_parallelize(cls, subtasks: List[str]) -> bool:
        """Determine if subtasks can be executed in parallel."""
        if len(subtasks) <= 1:
            return False

        # Check for dependency indicators
        dependency_keywords = ["then", "after", "before", "first", "finally", "depends"]
        for subtask in subtasks:
            if any(keyword in subtask.lower() for keyword in dependency_keywords):
                return False

        return True


def supervisor_node(state: AgentState) -> Command:
    """
    Main supervisor node that analyzes tasks and routes to specialists.

    Uses Command API to control workflow execution.
    """
    logger.info(f"Supervisor analyzing task for session {state['session_id']}")

    # Initialize model router
    router = ModelRouter()
    model = router.get_model(AgentType.SUPERVISOR)

    # Get latest message
    messages = state.get("messages", [])
    if not messages:
        return Command(
            goto="END",
            update={
                "errors": [{"error": "No messages to process", "timestamp": datetime.now().isoformat()}]
            }
        )

    latest_message = messages[-1]
    task_description = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)

    # Classify task
    task_type = TaskClassifier.classify_task(task_description)
    subtasks = TaskClassifier.identify_subtasks(task_description)
    can_parallelize = TaskClassifier.can_parallelize(subtasks)

    # Update state with classification
    state_update = {
        "task_description": task_description,
        "task_type": task_type,
        "subtasks": subtasks,
        "current_agent": "supervisor",
        "agent_statuses": {"supervisor": "completed"},
    }

    # Determine routing based on task type and complexity
    if can_parallelize and len(subtasks) > 1:
        # Route to parallel executor for independent subtasks
        logger.info(f"Routing to parallel executor for {len(subtasks)} subtasks")
        return Command(
            goto="parallel_executor",
            update=state_update
        )

    # Route to single specialist based on task type
    agent_routing = {
        "code_generation": "coder",
        "code_review": "reviewer",
        "research": "researcher",
        "design": "designer",
        "debugging": "coder",  # Coder handles debugging
        "refactoring": "coder",  # Coder handles refactoring
        "general": "researcher",  # Default to researcher for general queries
    }

    target_agent = agent_routing.get(task_type, "researcher")
    logger.info(f"Routing task of type '{task_type}' to {target_agent}")

    # Check if task involves git operations that need approval
    git_keywords = ["commit", "push", "merge", "pull request", "pr", "deploy"]
    requires_approval = any(keyword in task_description.lower() for keyword in git_keywords)

    state_update["requires_approval"] = requires_approval
    state_update["current_agent"] = target_agent
    state_update[f"agent_statuses"][target_agent] = "pending"

    return Command(
        goto=target_agent,
        update=state_update
    )


def parallel_executor_node(state: AgentState) -> List[Send]:
    """
    Executes multiple subtasks in parallel using Send API.

    Returns list of Send commands for parallel agent invocation.
    """
    logger.info(f"Parallel executor distributing {len(state['subtasks'])} subtasks")

    sends = []
    subtasks = state.get("subtasks", [])

    if not subtasks:
        # No subtasks to parallelize, route back to supervisor
        return Command(
            goto="supervisor",
            update={"errors": [{"error": "No subtasks to execute", "timestamp": datetime.now().isoformat()}]}
        )

    # Create Send command for each subtask
    for idx, subtask in enumerate(subtasks):
        # Classify each subtask
        task_type = TaskClassifier.classify_task(subtask)

        # Determine target agent
        agent_routing = {
            "code_generation": "coder",
            "code_review": "reviewer",
            "research": "researcher",
            "design": "designer",
            "debugging": "coder",
            "refactoring": "coder",
            "general": "researcher",
        }

        target_agent = agent_routing.get(task_type, "researcher")

        # Create parallel task state
        parallel_state = ParallelTaskState(
            session_id=state["session_id"],
            user_id=state["user_id"],
            task_id=f"task_{idx}",
            task_description=subtask,
            assigned_agent=target_agent,
            status="pending",
            result=None,
            error=None,
            model_name="",  # Will be set by agent
            max_tokens=4096,
            timeout_seconds=300,
        )

        # Create Send command
        sends.append(
            Send(
                node=target_agent,
                arg=parallel_state,
            )
        )

        logger.info(f"Dispatching subtask {idx} to {target_agent}: {subtask[:50]}...")

    return sends


def result_aggregator_node(state: AgentState) -> Command:
    """
    Aggregates results from parallel agent executions.

    Combines outputs and determines next steps.
    """
    logger.info("Aggregating results from parallel execution")

    # Collect all agent outputs
    agent_outputs = state.get("agent_outputs", [])
    completed_subtasks = state.get("completed_subtasks", [])

    # Check for any failures
    failures = [output for output in agent_outputs if output.get("error")]

    if failures:
        logger.warning(f"Found {len(failures)} failed subtasks")
        # Route to error handler or retry logic
        return Command(
            goto="error_handler",
            update={
                "errors": failures,
                "retry_count": state.get("retry_count", 0) + 1,
            }
        )

    # Check if any outputs require approval
    requires_approval = any(
        output.get("requires_approval") for output in agent_outputs
    )

    if requires_approval:
        logger.info("Outputs require human approval")
        return Command(
            goto="approval",
            update={
                "requires_approval": True,
                "current_agent": "approval",
            }
        )

    # All tasks completed successfully
    logger.info("All subtasks completed successfully")

    # Generate summary message
    summary_parts = ["Completed the following tasks:"]
    for idx, subtask in enumerate(completed_subtasks):
        summary_parts.append(f"{idx + 1}. {subtask}")

    summary_message = AIMessage(
        content="\n".join(summary_parts),
        metadata={
            "agent": "supervisor",
            "timestamp": datetime.now().isoformat(),
        }
    )

    return Command(
        goto="END",
        update={
            "messages": [summary_message],
            "completed_at": datetime.now(),
            "current_agent": None,
        }
    )


def error_handler_node(state: AgentState) -> Command:
    """
    Handles errors and determines retry strategy.

    Implements exponential backoff and fallback logic.
    """
    logger.info("Error handler processing failures")

    errors = state.get("errors", [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        logger.error(f"Max retries ({max_retries}) exceeded")
        error_message = AIMessage(
            content=f"Failed after {max_retries} attempts. Errors: {errors}",
            metadata={
                "agent": "error_handler",
                "timestamp": datetime.now().isoformat(),
                "error": True,
            }
        )

        return Command(
            goto="END",
            update={
                "messages": [error_message],
                "completed_at": datetime.now(),
                "current_agent": None,
            }
        )

    # Retry with fallback model or adjusted parameters
    logger.info(f"Retrying (attempt {retry_count + 1}/{max_retries})")

    # Route back to supervisor for retry
    return Command(
        goto="supervisor",
        update={
            "retry_count": retry_count + 1,
            "errors": errors,
        }
    )