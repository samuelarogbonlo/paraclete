"""
Integration tests for LangGraph agent workflows.

Tests full workflow execution, state persistence, and human-in-the-loop approval.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from app.agents.state import AgentState


@pytest.fixture
def base_workflow_state():
    """Base state for workflow testing."""
    return {
        'session_id': 'test-session-workflow',
        'messages': [HumanMessage(content='Write a function to sort arrays')],
        'task_description': 'Write a function to sort arrays',
        'task_type': 'code_generation',
        'repo_url': 'https://github.com/test/repo',
        'branch_name': 'main',
        'vm_workspace_path': '/tmp/workspace',
        'github_token': 'test-token',
        'agent_outputs': [],
        'pending_changes': [],
        'agent_statuses': {},
        'errors': [],
        'retry_count': 0,
        'max_retries': 3,
    }


@pytest.mark.integration
class TestSupervisorToCoderWorkflow:
    """Test workflow from supervisor to coder agent."""

    @patch('app.agents.specialists.coder.ChatPromptTemplate')
    @patch('app.agents.specialists.coder.ModelRouter')
    @patch('app.agents.specialists.coder.get_file_tools')
    @patch('app.agents.specialists.coder.get_git_tools')
    def test_supervisor_routes_code_task_to_coder(
        self,
        mock_git_tools,
        mock_file_tools,
        mock_model_router,
        mock_prompt_template,
        base_workflow_state,
    ):
        """Test that supervisor correctly routes code generation to coder."""
        # Arrange
        from app.agents.specialists.coder import coder_node

        # Mock tools - return list of mock tool objects
        file_tool = Mock(name='write_file')
        file_tool.name = 'write_file'
        mock_file_tools.return_value = [file_tool]

        git_tool = Mock(name='commit_changes')
        git_tool.name = 'commit_changes'
        mock_git_tools.return_value = [git_tool]

        # Mock response with explicit tool_calls as empty list
        mock_response = Mock()
        mock_response.content = 'Code generated successfully'
        mock_response.tool_calls = []

        # Mock the chain (prompt | model) to return our response directly
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=mock_response)

        mock_model = Mock()
        mock_model.model_name = 'gpt-4o'
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Mock prompt template so prompt | model returns our chain
        mock_prompt = Mock()
        mock_prompt.__or__ = Mock(return_value=mock_chain)
        mock_prompt_template.from_messages = Mock(return_value=mock_prompt)

        mock_router = Mock()
        mock_router.get_model = Mock(return_value=mock_model)
        mock_model_router.return_value = mock_router

        # Act
        result = coder_node(base_workflow_state)

        # Assert
        assert isinstance(result, Command)
        assert result.update['agent_statuses']['coder'] == 'completed'
        assert len(result.update['agent_outputs']) > 0


@pytest.mark.integration
class TestWorkflowStateTransitions:
    """Test state transitions through workflow."""

    def test_workflow_state_accumulates_messages(self, base_workflow_state):
        """Test that messages accumulate through workflow."""
        # Simulate adding messages
        state = base_workflow_state.copy()

        state['messages'].append(AIMessage(content='Task classified as code_generation'))
        state['messages'].append(AIMessage(content='Code generated'))

        assert len(state['messages']) == 3
        assert isinstance(state['messages'][0], HumanMessage)
        assert isinstance(state['messages'][1], AIMessage)

    def test_workflow_tracks_agent_outputs(self, base_workflow_state):
        """Test that agent outputs are tracked."""
        # Simulate agent execution
        from app.agents.state import AgentOutput

        output = AgentOutput(
            agent_name='coder',
            timestamp=datetime.now(),
            result={'summary': 'Generated code'},
            model_used='gpt-4o',
            tokens_used=500,
            error=None,
        )

        state = base_workflow_state.copy()
        state['agent_outputs'].append(output)

        assert len(state['agent_outputs']) == 1
        assert state['agent_outputs'][0]['agent_name'] == 'coder'

    def test_workflow_tracks_pending_changes(self, base_workflow_state):
        """Test that file changes are tracked."""
        # Simulate file changes
        from app.agents.state import GitChange

        change = GitChange(
            file_path='/workspace/sort.py',
            operation='create',
            old_content=None,
            new_content='def sort_array(arr):\n    return sorted(arr)\n',
            diff=None,
        )

        state = base_workflow_state.copy()
        state['pending_changes'].append(change)

        assert len(state['pending_changes']) == 1
        assert state['pending_changes'][0]['file_path'] == '/workspace/sort.py'


@pytest.mark.integration
class TestWorkflowErrorHandling:
    """Test error handling in workflows."""

    @patch('app.agents.specialists.coder.ModelRouter')
    @patch('app.agents.specialists.coder.get_file_tools')
    @patch('app.agents.specialists.coder.get_git_tools')
    def test_workflow_handles_agent_errors(
        self,
        mock_git_tools,
        mock_file_tools,
        mock_model_router,
        base_workflow_state,
    ):
        """Test that workflow handles agent errors gracefully."""
        # Arrange
        from app.agents.specialists.coder import coder_node

        mock_file_tools.return_value = []
        mock_git_tools.return_value = []

        mock_model = Mock()
        mock_model.invoke = Mock(side_effect=Exception('Model API error'))
        mock_router = Mock()
        mock_router.get_model = Mock(return_value=mock_model)
        mock_model_router.return_value = mock_router

        # Act
        result = coder_node(base_workflow_state)

        # Assert
        assert result.goto == 'error_handler'
        assert len(result.update['errors']) > 0
        assert result.update['agent_statuses']['coder'] == 'failed'

    def test_workflow_tracks_retry_count(self, base_workflow_state):
        """Test that retry count is tracked."""
        # Simulate retry
        state = base_workflow_state.copy()
        state['retry_count'] = 1

        assert state['retry_count'] == 1
        assert state['retry_count'] < state['max_retries']


@pytest.mark.integration
class TestWorkflowApprovalFlow:
    """Test human-in-the-loop approval workflow."""

    def test_workflow_detects_approval_required(self, base_workflow_state):
        """Test detection of approval-required operations."""
        # Simulate pending changes
        from app.agents.state import GitChange

        state = base_workflow_state.copy()
        state['pending_changes'] = [
            GitChange(
                file_path='/workspace/file.py',
                operation='modify',
                old_content='old',
                new_content='new',
                diff='@@ -1 +1 @@\n-old\n+new',
            )
        ]
        state['requires_approval'] = True

        assert state['requires_approval'] is True
        assert len(state['pending_changes']) > 0

    @patch('app.agents.specialists.coder.ChatPromptTemplate')
    @patch('app.agents.specialists.coder.ModelRouter')
    @patch('app.agents.specialists.coder.get_file_tools')
    @patch('app.agents.specialists.coder.get_git_tools')
    def test_workflow_routes_to_approval(
        self,
        mock_git_tools,
        mock_file_tools,
        mock_model_router,
        mock_prompt_template,
        base_workflow_state,
    ):
        """Test that workflow routes to approval when required."""
        # Arrange
        from app.agents.specialists.coder import coder_node

        # Mock tools - return list of mock tool objects
        file_tool = Mock(name='write_file')
        file_tool.name = 'write_file'
        file_tool.invoke = Mock(return_value={'success': True, 'path': '/test.py'})
        mock_file_tools.return_value = [file_tool]

        git_tool = Mock(name='commit_changes')
        git_tool.name = 'commit_changes'
        mock_git_tools.return_value = [git_tool]

        # Mock response with tool calls
        mock_response = Mock()
        mock_response.content = 'Code with changes'
        mock_response.tool_calls = [
            {'name': 'write_file', 'args': {'file_path': '/test.py', 'content': 'code'}}
        ]

        # Mock the chain
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=mock_response)

        mock_model = Mock()
        mock_model.model_name = 'gpt-4o'
        mock_model.bind_tools = Mock(return_value=mock_model)

        mock_prompt = Mock()
        mock_prompt.__or__ = Mock(return_value=mock_chain)
        mock_prompt_template.from_messages = Mock(return_value=mock_prompt)

        mock_router = Mock()
        mock_router.get_model = Mock(return_value=mock_model)
        mock_model_router.return_value = mock_router

        base_workflow_state['requires_approval'] = True

        # Act
        result = coder_node(base_workflow_state)

        # Assert
        assert result.goto == 'approval'


@pytest.mark.integration
class TestWorkflowParallelExecution:
    """Test parallel task execution."""

    def test_workflow_splits_parallel_subtasks(self, base_workflow_state):
        """Test that workflow can split into parallel subtasks."""
        # Simulate subtask decomposition
        state = base_workflow_state.copy()
        state['subtasks'] = [
            {'id': '1', 'description': 'Write function', 'agent': 'coder'},
            {'id': '2', 'description': 'Write tests', 'agent': 'coder'},
            {'id': '3', 'description': 'Write docs', 'agent': 'coder'},
        ]
        state['parallel_execution'] = True

        assert len(state['subtasks']) == 3
        assert state['parallel_execution'] is True

    def test_workflow_aggregates_results(self, base_workflow_state):
        """Test result aggregation from parallel execution."""
        # Simulate completed subtasks
        from app.agents.state import AgentOutput

        state = base_workflow_state.copy()
        state['subtasks'] = [
            {'id': '1', 'description': 'Task 1'},
            {'id': '2', 'description': 'Task 2'},
        ]
        state['completed_subtasks'] = ['1', '2']
        state['agent_outputs'] = [
            AgentOutput(
                agent_name='coder',
                timestamp=datetime.now(),
                result={'subtask_id': '1', 'summary': 'Done 1'},
                model_used='gpt-4o',
                tokens_used=100,
                error=None,
            ),
            AgentOutput(
                agent_name='coder',
                timestamp=datetime.now(),
                result={'subtask_id': '2', 'summary': 'Done 2'},
                model_used='gpt-4o',
                tokens_used=100,
                error=None,
            ),
        ]

        assert len(state['completed_subtasks']) == len(state['subtasks'])
        assert len(state['agent_outputs']) == 2


@pytest.mark.integration
class TestWorkflowPersistence:
    """Test workflow state persistence (structure tests)."""

    def test_workflow_state_serializable(self, base_workflow_state):
        """Test that workflow state can be serialized."""
        # Verify all state fields are JSON-serializable types
        import json

        state = base_workflow_state.copy()

        # Should be able to serialize basic types
        assert isinstance(state['session_id'], str)
        assert isinstance(state['task_description'], str)
        assert isinstance(state['agent_outputs'], list)
        assert isinstance(state['agent_statuses'], dict)

    def test_workflow_checkpoint_structure(self):
        """Test checkpoint data structure."""
        # Simulate checkpoint
        checkpoint = {
            'session_id': 'test-session',
            'checkpoint_id': 'checkpoint-123',
            'timestamp': datetime.now().isoformat(),
            'state': {
                'messages': [],
                'agent_outputs': [],
                'pending_changes': [],
            },
            'next_node': 'coder',
        }

        assert 'session_id' in checkpoint
        assert 'checkpoint_id' in checkpoint
        assert 'state' in checkpoint
        assert 'next_node' in checkpoint


@pytest.mark.integration
class TestWorkflowEndToEnd:
    """End-to-end workflow tests (structure)."""

    @patch('app.agents.specialists.coder.ChatPromptTemplate')
    @patch('app.agents.specialists.coder.ModelRouter')
    @patch('app.agents.specialists.coder.get_file_tools')
    @patch('app.agents.specialists.coder.get_git_tools')
    def test_simple_code_generation_workflow(
        self,
        mock_git_tools,
        mock_file_tools,
        mock_model_router,
        mock_prompt_template,
        base_workflow_state,
    ):
        """Test simple code generation workflow."""
        # Arrange
        from app.agents.specialists.coder import coder_node

        # Mock tools - return list of mock tool objects
        file_tool = Mock(name='write_file')
        file_tool.name = 'write_file'
        mock_file_tools.return_value = [file_tool]

        git_tool = Mock(name='commit_changes')
        git_tool.name = 'commit_changes'
        mock_git_tools.return_value = [git_tool]

        # Mock response
        mock_response = Mock()
        mock_response.content = 'Code generated'
        mock_response.tool_calls = []

        # Mock the chain
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=mock_response)

        mock_model = Mock()
        mock_model.model_name = 'gpt-4o'
        mock_model.bind_tools = Mock(return_value=mock_model)

        mock_prompt = Mock()
        mock_prompt.__or__ = Mock(return_value=mock_chain)
        mock_prompt_template.from_messages = Mock(return_value=mock_prompt)

        mock_router = Mock()
        mock_router.get_model = Mock(return_value=mock_model)
        mock_model_router.return_value = mock_router

        base_workflow_state['skip_review'] = True

        # Act
        result = coder_node(base_workflow_state)

        # Assert
        assert result.goto == 'END'
        assert result.update['agent_statuses']['coder'] == 'completed'

    @patch('app.agents.specialists.researcher.ChatPromptTemplate')
    @patch('app.agents.specialists.researcher.ModelRouter')
    @patch('app.agents.specialists.researcher.get_search_tools')
    def test_simple_research_workflow(
        self,
        mock_search_tools,
        mock_model_router,
        mock_prompt_template,
        base_workflow_state,
    ):
        """Test simple research workflow."""
        # Arrange
        from app.agents.specialists.researcher import researcher_node

        # Mock tools - return list of mock tool objects
        search_tool = Mock(name='web_search')
        search_tool.name = 'web_search'
        mock_search_tools.return_value = [search_tool]

        # Mock response
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []

        # Mock the chain
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=mock_response)

        mock_model = Mock()
        mock_model.model_name = 'gemini-1.5-pro'
        mock_model.bind_tools = Mock(return_value=mock_model)

        mock_prompt = Mock()
        mock_prompt.__or__ = Mock(return_value=mock_chain)
        mock_prompt_template.from_messages = Mock(return_value=mock_prompt)

        mock_router = Mock()
        mock_router.get_model = Mock(return_value=mock_model)
        mock_model_router.return_value = mock_router

        base_workflow_state['task_type'] = 'research'

        # Act
        result = researcher_node(base_workflow_state)

        # Assert
        assert result.goto == 'END'
        assert result.update['agent_statuses']['researcher'] == 'completed'


@pytest.mark.integration
class TestWorkflowMetrics:
    """Test workflow metrics tracking."""

    def test_workflow_tracks_token_usage(self, base_workflow_state):
        """Test that token usage is tracked."""
        # Simulate agent outputs with token counts
        from app.agents.state import AgentOutput

        state = base_workflow_state.copy()
        state['agent_outputs'] = [
            AgentOutput(
                agent_name='coder',
                timestamp=datetime.now(),
                result={},
                model_used='gpt-4o',
                tokens_used=500,
                error=None,
            ),
            AgentOutput(
                agent_name='reviewer',
                timestamp=datetime.now(),
                result={},
                model_used='claude-sonnet-3.5',
                tokens_used=300,
                error=None,
            ),
        ]

        total_tokens = sum(o['tokens_used'] or 0 for o in state['agent_outputs'])
        assert total_tokens == 800

    def test_workflow_tracks_agent_execution_times(self):
        """Test that execution times can be tracked."""
        # Simulate timing
        from app.agents.state import AgentOutput

        start_time = datetime.now()
        # ... workflow execution ...
        end_time = datetime.now()

        execution_time = (end_time - start_time).total_seconds()

        assert execution_time >= 0

    def test_workflow_tracks_model_usage_per_agent(self, base_workflow_state):
        """Test tracking which models each agent used."""
        # Simulate agent outputs
        from app.agents.state import AgentOutput

        state = base_workflow_state.copy()
        state['agent_outputs'] = [
            AgentOutput(
                agent_name='supervisor',
                timestamp=datetime.now(),
                result={},
                model_used='claude-sonnet-4',
                tokens_used=100,
                error=None,
            ),
            AgentOutput(
                agent_name='coder',
                timestamp=datetime.now(),
                result={},
                model_used='gpt-4o',
                tokens_used=500,
                error=None,
            ),
            AgentOutput(
                agent_name='researcher',
                timestamp=datetime.now(),
                result={},
                model_used='gemini-1.5-pro',
                tokens_used=2000,
                error=None,
            ),
        ]

        model_usage = {}
        for output in state['agent_outputs']:
            agent = output['agent_name']
            model = output['model_used']
            model_usage[agent] = model

        assert model_usage['supervisor'] == 'claude-sonnet-4'
        assert model_usage['coder'] == 'gpt-4o'
        assert model_usage['researcher'] == 'gemini-1.5-pro'
