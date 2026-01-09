"""
LangGraph Agent State definitions using TypedDict.

This module defines the state structure for the multi-agent orchestration system.
All agents share this state for coordination and communication.
"""

from typing import TypedDict, Annotated, Literal, Any, Optional
from datetime import datetime
from langgraph.graph import add_messages


class GitChange(TypedDict):
    """Structure for tracking file changes in git operations."""

    file_path: str
    operation: Literal["create", "modify", "delete"]
    old_content: Optional[str]
    new_content: Optional[str]
    diff: Optional[str]


class AgentOutput(TypedDict):
    """Structure for agent execution results."""

    agent_name: str
    timestamp: datetime
    result: Any
    model_used: str
    tokens_used: Optional[int]
    error: Optional[str]


class ApprovalRequest(TypedDict):
    """Structure for human approval requests."""

    request_id: str
    type: Literal["git_push", "file_write", "command_execution", "api_call"]
    description: str
    details: dict
    requested_at: datetime
    approved: Optional[bool]
    approved_by: Optional[str]
    approved_at: Optional[datetime]


class AgentState(TypedDict):
    """
    Shared state for all agents in the LangGraph workflow.

    This state is immutable and updates create new versions for checkpointing.
    """

    # Message history using LangGraph's add_messages reducer
    messages: Annotated[list, add_messages]

    # Session context
    session_id: str
    user_id: str
    project_name: Optional[str]

    # Voice interaction
    voice_transcript: Optional[str]
    voice_audio_url: Optional[str]

    # Agent coordination
    current_agent: Optional[str]
    agent_statuses: dict[str, Literal["pending", "running", "completed", "failed", "interrupted"]]
    agent_outputs: list[AgentOutput]

    # Task management
    task_description: str
    task_type: Optional[Literal["code_generation", "code_review", "research", "design", "debugging", "refactoring"]]
    subtasks: list[str]  # Decomposed subtasks for parallel execution
    completed_subtasks: list[str]

    # Git and file context
    repo_url: Optional[str]
    branch_name: Optional[str]
    base_branch: Optional[str]
    pending_changes: list[GitChange]
    committed_files: list[str]

    # Approval workflow
    requires_approval: bool
    approval_requests: list[ApprovalRequest]
    approval_checkpoint_id: Optional[str]

    # Model routing preferences
    preferred_models: dict[str, str]  # agent_name -> model_name
    model_fallbacks: dict[str, list[str]]  # model_name -> [fallback_models]

    # Execution metadata
    started_at: datetime
    completed_at: Optional[datetime]
    total_tokens_used: int
    total_cost_usd: float

    # Error handling
    errors: list[dict]
    retry_count: int
    max_retries: int

    # VM context (for file operations)
    vm_machine_id: Optional[str]
    vm_workspace_path: Optional[str]

    # Interrupt and resume
    interrupt_reason: Optional[str]
    resume_data: Optional[dict]
    checkpoint_id: Optional[str]

    # Search and research context
    search_results: list[dict]
    documentation_sources: list[str]
    research_summary: Optional[str]

    # Code review context
    review_comments: list[dict]
    security_issues: list[dict]
    performance_issues: list[dict]

    # Design context
    architecture_decisions: list[dict]
    design_patterns: list[str]
    system_diagrams: list[dict]


class ParallelTaskState(TypedDict):
    """
    State for parallel task execution using Send API.

    This is a subset of AgentState used for parallel agent invocations.
    """

    # Core context from parent state
    session_id: str
    user_id: str

    # Task specific
    task_id: str
    task_description: str
    assigned_agent: str

    # Execution
    status: Literal["pending", "running", "completed", "failed"]
    result: Optional[Any]
    error: Optional[str]

    # Resources
    model_name: str
    max_tokens: int
    timeout_seconds: int


class CheckpointMetadata(TypedDict):
    """Metadata stored with LangGraph checkpoints."""

    checkpoint_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    agent_name: str
    checkpoint_type: Literal["approval", "error", "completion", "interrupt"]
    description: str
    can_resume: bool