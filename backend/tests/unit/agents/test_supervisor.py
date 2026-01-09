"""
Unit tests for supervisor agent with Command API routing.

Tests task classification, parallel execution, and routing logic.
"""

import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from langgraph.constants import Send

from app.agents.supervisor import (
    supervisor_node,
    parallel_executor_node,
    result_aggregator_node,
    error_handler_node,
    TaskClassifier,
)
from app.agents.state import AgentState, ParallelTaskState


class TestTaskClassifier:
    """Test task classification and decomposition logic."""

    def test_classify_code_generation(self):
        """Task classifier should identify code generation tasks."""
        tasks = [
            "create a new function to sort arrays",
            "implement user authentication",
            "build a REST API endpoint for users",
            "write a component for rendering data",
            "generate code for file upload",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "code_generation", f"Failed for task: {task}"

    def test_classify_code_review(self):
        """Task classifier should identify code review tasks."""
        tasks = [
            "review this pull request",
            "check the code for bugs",
            "analyze security vulnerabilities",
            "perform a code review",
            "find performance issues in this code",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "code_review", f"Failed for task: {task}"

    def test_classify_research(self):
        """Task classifier should identify research tasks."""
        tasks = [
            "search for information about React hooks",
            "find documentation on LangGraph",
            "research best practices for async Python",
            "what is the latest version of FastAPI",
            "how to implement WebSockets in Flutter",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "research", f"Failed for task: {task}"

    def test_classify_design(self):
        """Task classifier should identify design tasks."""
        tasks = [
            "design the system architecture",
            "create a database schema",
            "plan the UI layout",
            "architect a microservices solution",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "design", f"Failed for task: {task}"

    def test_classify_debugging(self):
        """Task classifier should identify debugging tasks."""
        tasks = [
            "debug this error",
            "fix the crashing application",
            "solve the authentication issue",
            "this is not working properly",
            "resolve the exception in login",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "debugging", f"Failed for task: {task}"

    def test_classify_refactoring(self):
        """Task classifier should identify refactoring tasks."""
        tasks = [
            "refactor the user service",
            "optimize database queries",
            "improve performance of this function",
            "clean up the codebase",
        ]

        for task in tasks:
            result = TaskClassifier.classify_task(task)
            assert result == "refactoring", f"Failed for task: {task}"

    def test_classify_general_fallback(self):
        """Task classifier should fall back to general for unknown tasks."""
        task = "tell me a joke about programming"
        result = TaskClassifier.classify_task(task)
        assert result == "general"

    def test_identify_numbered_subtasks(self):
        """Should extract numbered list subtasks."""
        task = """
        Complete the following:
        1. Create user model
        2. Add database migration
        3. Implement API endpoints
        4. Write tests
        """

        subtasks = TaskClassifier.identify_subtasks(task)

        assert len(subtasks) == 4
        assert "Create user model" in subtasks
        assert "Add database migration" in subtasks
        assert "Implement API endpoints" in subtasks
        assert "Write tests" in subtasks

    def test_identify_bullet_subtasks(self):
        """Should extract bullet point subtasks."""
        task = """
        Please do the following:
        - Fix authentication bug
        - Update documentation
        - Deploy to staging
        """

        subtasks = TaskClassifier.identify_subtasks(task)

        assert len(subtasks) == 3
        assert "Fix authentication bug" in subtasks
        assert "Update documentation" in subtasks
        assert "Deploy to staging" in subtasks

    def test_identify_and_separated_subtasks(self):
        """Should extract 'and' separated subtasks."""
        task = "Create a login form and implement validation and add error handling"

        subtasks = TaskClassifier.identify_subtasks(task)

        assert len(subtasks) == 3
        assert any("login form" in s for s in subtasks)
        assert any("validation" in s for s in subtasks)
        assert any("error handling" in s for s in subtasks)

    def test_can_parallelize_independent_tasks(self):
        """Should identify parallelizable independent tasks."""
        subtasks = [
            "Create user model",
            "Create product model",
            "Create order model",
        ]

        result = TaskClassifier.can_parallelize(subtasks)
        assert result is True

    def test_cannot_parallelize_dependent_tasks(self):
        """Should not parallelize tasks with dependencies."""
        subtasks = [
            "First create the database schema",
            "Then add migration files",
            "After that, run the migrations",
        ]

        result = TaskClassifier.can_parallelize(subtasks)
        assert result is False

    def test_cannot_parallelize_single_task(self):
        """Should not parallelize single task."""
        subtasks = ["Create user model"]

        result = TaskClassifier.can_parallelize(subtasks)
        assert result is False


class TestSupervisorNode:
    """Test supervisor node routing logic."""

    def test_supervisor_routes_coding_task(self):
        """Supervisor should route coding tasks to coder agent."""
        state = AgentState(
            messages=[HumanMessage(content="Create a function to calculate fibonacci")],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert isinstance(result, Command)
        assert result.goto == "coder"
        assert result.update["task_type"] == "code_generation"
        assert result.update["current_agent"] == "coder"

    def test_supervisor_routes_review_task(self):
        """Supervisor should route review tasks to reviewer agent."""
        state = AgentState(
            messages=[HumanMessage(content="Review this pull request for security issues")],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert isinstance(result, Command)
        assert result.goto == "reviewer"
        assert result.update["task_type"] == "code_review"

    def test_supervisor_routes_research_task(self):
        """Supervisor should route research tasks to researcher agent."""
        state = AgentState(
            messages=[HumanMessage(content="Find documentation about LangGraph checkpointing")],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert isinstance(result, Command)
        assert result.goto == "researcher"
        assert result.update["task_type"] == "research"

    def test_supervisor_routes_to_parallel_executor(self):
        """Supervisor should route to parallel executor for multiple independent tasks."""
        state = AgentState(
            messages=[
                HumanMessage(
                    content="""
                    Complete these tasks:
                    - Create user model
                    - Create product model
                    - Create order model
                    """
                )
            ],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert isinstance(result, Command)
        assert result.goto == "parallel_executor"
        assert len(result.update["subtasks"]) > 1

    def test_supervisor_detects_approval_required(self):
        """Supervisor should detect when git operations require approval."""
        state = AgentState(
            messages=[HumanMessage(content="Commit these changes and push to main")],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert result.update["requires_approval"] is True

    def test_supervisor_handles_no_messages(self):
        """Supervisor should handle empty message list gracefully."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = supervisor_node(state)

        assert isinstance(result, Command)
        assert result.goto == "END"
        assert len(result.update["errors"]) > 0


class TestParallelExecutorNode:
    """Test parallel task execution with Send API."""

    def test_parallel_executor_creates_send_commands(self):
        """Parallel executor should create Send commands for each subtask."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=["Create user model", "Create product model", "Create order model"],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = parallel_executor_node(state)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(send, Send) for send in result)

    def test_parallel_executor_routes_tasks_correctly(self):
        """Parallel executor should route each subtask to appropriate agent."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[
                "Create a login function",
                "Review the authentication code",
                "Research OAuth best practices",
            ],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = parallel_executor_node(state)

        assert isinstance(result, list)
        assert len(result) == 3

        # Verify each send has correct agent assignment
        agents = [send.node for send in result]
        assert "coder" in agents
        assert "reviewer" in agents
        assert "researcher" in agents


class TestResultAggregatorNode:
    """Test result aggregation from parallel execution."""

    def test_aggregator_completes_on_success(self):
        """Aggregator should complete workflow when all tasks succeed."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[
                {"agent": "coder", "result": "Created model", "error": None},
                {"agent": "reviewer", "result": "Review complete", "error": None},
            ],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=["Create model", "Review code"],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = result_aggregator_node(state)

        assert isinstance(result, Command)
        assert result.goto == "END"
        assert result.update["current_agent"] is None

    def test_aggregator_routes_to_approval_when_needed(self):
        """Aggregator should route to approval when outputs require it."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[
                {
                    "agent": "coder",
                    "result": "Ready to commit",
                    "error": None,
                    "requires_approval": True,
                },
            ],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=["Create feature"],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = result_aggregator_node(state)

        assert isinstance(result, Command)
        assert result.goto == "approval"
        assert result.update["requires_approval"] is True

    def test_aggregator_routes_to_error_handler_on_failures(self):
        """Aggregator should route to error handler when tasks fail."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[
                {"agent": "coder", "result": None, "error": "Failed to create model"},
            ],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = result_aggregator_node(state)

        assert isinstance(result, Command)
        assert result.goto == "error_handler"


class TestErrorHandlerNode:
    """Test error handling and retry logic."""

    def test_error_handler_retries_on_failure(self):
        """Error handler should retry failed tasks."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[{"error": "API timeout", "timestamp": datetime.now().isoformat()}],
            retry_count=0,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = error_handler_node(state)

        assert isinstance(result, Command)
        assert result.goto == "supervisor"
        assert result.update["retry_count"] == 1

    def test_error_handler_gives_up_after_max_retries(self):
        """Error handler should give up after max retries."""
        state = AgentState(
            messages=[],
            session_id="test-session-123",
            user_id="user-456",
            project_name=None,
            voice_transcript=None,
            voice_audio_url=None,
            current_agent=None,
            agent_statuses={},
            agent_outputs=[],
            task_description="",
            task_type=None,
            subtasks=[],
            completed_subtasks=[],
            repo_url=None,
            branch_name=None,
            base_branch=None,
            pending_changes=[],
            committed_files=[],
            requires_approval=False,
            approval_requests=[],
            approval_checkpoint_id=None,
            preferred_models={},
            model_fallbacks={},
            started_at=datetime.now(),
            completed_at=None,
            total_tokens_used=0,
            total_cost_usd=0.0,
            errors=[{"error": "API timeout", "timestamp": datetime.now().isoformat()}],
            retry_count=3,
            max_retries=3,
            vm_machine_id=None,
            vm_workspace_path=None,
            interrupt_reason=None,
            resume_data=None,
            checkpoint_id=None,
            search_results=[],
            documentation_sources=[],
            research_summary=None,
            review_comments=[],
            security_issues=[],
            performance_issues=[],
            architecture_decisions=[],
            design_patterns=[],
            system_diagrams=[],
        )

        result = error_handler_node(state)

        assert isinstance(result, Command)
        assert result.goto == "END"
        assert result.update["current_agent"] is None
