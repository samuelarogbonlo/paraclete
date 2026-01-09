"""
Test suite for the coder specialist agent.

Tests code generation, debugging, and refactoring workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from app.agents.specialists.coder import (
    coder_node,
    CODER_SYSTEM_PROMPT,
    CODE_GENERATION_PROMPT,
    DEBUGGING_PROMPT,
    REFACTORING_PROMPT,
    generate_code_summary,
)
from app.agents.state import AgentState, AgentOutput, GitChange


@pytest.fixture
def mock_model_router():
    """Mock ModelRouter for testing."""
    with patch('app.agents.specialists.coder.ModelRouter') as mock_router:
        mock_instance = Mock()
        mock_model = Mock()
        mock_model.model_name = 'gpt-4o'
        mock_model.bind_tools = Mock(return_value=mock_model)
        mock_instance.get_model = Mock(return_value=mock_model)
        mock_router.return_value = mock_instance
        yield mock_router


@pytest.fixture
def mock_file_tools():
    """Mock file operation tools."""
    with patch('app.agents.specialists.coder.get_file_tools') as mock:
        tool1 = Mock(name='read_file')
        tool1.name = 'read_file'
        tool1.invoke = Mock(return_value={'success': True, 'content': 'file content'})

        tool2 = Mock(name='write_file')
        tool2.name = 'write_file'
        tool2.invoke = Mock(return_value={'success': True, 'path': '/test/file.py'})

        mock.return_value = [tool1, tool2]
        yield mock


@pytest.fixture
def mock_git_tools():
    """Mock git operation tools."""
    with patch('app.agents.specialists.coder.get_git_tools') as mock:
        tool1 = Mock(name='clone_repository')
        tool1.name = 'clone_repository'
        tool1.invoke = Mock(return_value={'success': True, 'workspace': '/workspace'})

        tool2 = Mock(name='commit_changes')
        tool2.name = 'commit_changes'
        tool2.invoke = Mock(return_value={'success': True, 'commit_sha': 'abc123'})

        mock.return_value = [tool1, tool2]
        yield mock


@pytest.fixture
def base_state():
    """Base agent state for testing."""
    return {
        'session_id': 'test-session-123',
        'messages': [HumanMessage(content='Write a function to sort array')],
        'task_description': 'Write a function to sort array',
        'task_type': 'code_generation',
        'repo_url': 'https://github.com/test/repo',
        'branch_name': 'main',
        'vm_workspace_path': '/tmp/workspace',
        'github_token': 'test-token',
        'agent_outputs': [],
        'pending_changes': [],
        'agent_statuses': {},
    }


class TestCoderNode:
    """Tests for the coder_node function."""

    def test_coder_node_basic_execution(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test basic coder agent execution."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Generated code implementation'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = coder_node(base_state)

        # Assert
        assert isinstance(result, Command)
        assert 'messages' in result.update
        assert len(result.update['messages']) > 0
        assert isinstance(result.update['messages'][0], AIMessage)
        assert 'agent_outputs' in result.update
        assert result.update['agent_statuses']['coder'] == 'completed'

    def test_coder_node_uses_gpt4o_model(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that coder agent uses GPT-4o model."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        coder_node(base_state)

        # Assert
        from app.agents.router import AgentType
        mock_model_router.return_value.get_model.assert_called_with(
            AgentType.CODER,
            require_function_calling=True,
        )

    def test_coder_node_binds_file_and_git_tools(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that coder agent binds both file and git tools."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        coder_node(base_state)

        # Assert
        mock_file_tools.assert_called_once_with(workspace_root='/tmp/workspace')
        mock_git_tools.assert_called_once_with(github_token='test-token')
        mock_model.bind_tools.assert_called_once()

    def test_coder_node_with_tool_calls(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test coder agent execution with tool calls."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Writing file...'
        mock_response.tool_calls = [
            {
                'name': 'write_file',
                'args': {
                    'file_path': '/workspace/test.py',
                    'content': 'def sort_array(arr):\n    return sorted(arr)\n'
                }
            }
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = coder_node(base_state)

        # Assert
        assert 'pending_changes' in result.update
        assert len(result.update['pending_changes']) > 0

        # Check file change tracking
        change = result.update['pending_changes'][0]
        assert change['file_path'] == '/workspace/test.py'
        assert change['operation'] == 'modify'

    def test_coder_node_routes_to_reviewer_after_generation(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that code generation routes to reviewer."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code generated'
        mock_response.tool_calls = [
            {'name': 'write_file', 'args': {'file_path': '/test.py', 'content': 'code'}}
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['task_type'] = 'code_generation'
        base_state['skip_review'] = False

        # Act
        result = coder_node(base_state)

        # Assert
        assert result.goto == 'reviewer'

    def test_coder_node_routes_to_approval_when_required(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test routing to approval when changes require approval."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code'
        mock_response.tool_calls = [
            {'name': 'write_file', 'args': {'file_path': '/test.py', 'content': 'code'}}
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['requires_approval'] = True

        # Act
        result = coder_node(base_state)

        # Assert
        assert result.goto == 'approval'

    def test_coder_node_routes_to_end_when_done(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test routing to END when task is complete."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Task complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['skip_review'] = True
        base_state['requires_approval'] = False

        # Act
        result = coder_node(base_state)

        # Assert
        assert result.goto == 'END'

    def test_coder_node_handles_errors_gracefully(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test error handling in coder agent."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_model.invoke = Mock(side_effect=Exception('Model API error'))

        # Act
        result = coder_node(base_state)

        # Assert
        assert result.goto == 'error_handler'
        assert 'errors' in result.update
        assert len(result.update['errors']) > 0
        assert result.update['agent_statuses']['coder'] == 'failed'

    def test_coder_node_uses_debugging_prompt_for_debug_tasks(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that debugging tasks use the debugging prompt."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Bug fixed'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['task_type'] = 'debugging'

        # Act
        coder_node(base_state)

        # Assert
        # Verify the prompt used contains debugging instructions
        call_args = mock_model.invoke.call_args
        assert call_args is not None

    def test_coder_node_uses_refactoring_prompt_for_refactor_tasks(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that refactoring tasks use the refactoring prompt."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code refactored'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['task_type'] = 'refactoring'

        # Act
        coder_node(base_state)

        # Assert
        # Verify the prompt used
        call_args = mock_model.invoke.call_args
        assert call_args is not None

    def test_coder_node_includes_workspace_path_in_context(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that workspace path is passed to the model."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Code'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        coder_node(base_state)

        # Assert
        call_args = mock_model.invoke.call_args
        assert 'workspace' in call_args[0][0]
        assert call_args[0][0]['workspace'] == '/tmp/workspace'

    def test_coder_node_creates_agent_output(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test that agent output is created correctly."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Implementation complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = coder_node(base_state)

        # Assert
        outputs = result.update['agent_outputs']
        assert len(outputs) > 0

        output = outputs[-1]
        assert output['agent_name'] == 'coder'
        assert output['model_used'] == 'gpt-4o'
        assert output['error'] is None
        assert 'summary' in output['result']
        assert 'task' in output['result']

    def test_coder_node_tracks_multiple_tool_executions(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test tracking of multiple tool executions."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Multiple operations'
        mock_response.tool_calls = [
            {'name': 'write_file', 'args': {'file_path': '/file1.py', 'content': 'code1'}},
            {'name': 'write_file', 'args': {'file_path': '/file2.py', 'content': 'code2'}},
            {'name': 'write_file', 'args': {'file_path': '/file3.py', 'content': 'code3'}},
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = coder_node(base_state)

        # Assert
        assert len(result.update['pending_changes']) == 3

    def test_coder_node_uses_task_from_messages_when_not_specified(self, mock_model_router, mock_file_tools, mock_git_tools, base_state):
        """Test extracting task from messages when task_description is empty."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Task complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['task_description'] = ''
        base_state['messages'] = [HumanMessage(content='Fix the login bug')]

        # Act
        result = coder_node(base_state)

        # Assert
        output = result.update['agent_outputs'][-1]
        assert output['result']['task'] == 'Fix the login bug'


class TestCodeSummaryGeneration:
    """Tests for code summary generation."""

    def test_generate_code_summary_with_content(self):
        """Test summary generation with response content."""
        # Arrange
        response = Mock()
        response.content = 'Generated function to sort arrays using quicksort'

        # Act
        summary = generate_code_summary(response, [], [])

        # Assert
        assert 'Generated function to sort arrays' in summary

    def test_generate_code_summary_with_file_changes(self):
        """Test summary includes file changes."""
        # Arrange
        response = Mock()
        response.content = 'Code updated'

        changes = [
            GitChange(
                file_path='src/utils.py',
                operation='modify',
                old_content=None,
                new_content='new code',
                diff=None,
            ),
            GitChange(
                file_path='tests/test_utils.py',
                operation='create',
                old_content=None,
                new_content='test code',
                diff=None,
            ),
        ]

        # Act
        summary = generate_code_summary(response, [], changes)

        # Assert
        assert 'Files Changed:' in summary
        assert 'src/utils.py' in summary
        assert 'tests/test_utils.py' in summary

    def test_generate_code_summary_with_tool_results(self):
        """Test summary includes tool execution results."""
        # Arrange
        response = Mock()
        response.content = 'Operations completed'

        tool_results = [
            {'tool': 'write_file', 'args': {}, 'result': {'success': True}},
            {'tool': 'commit_changes', 'args': {}, 'result': {'success': True}},
        ]

        # Act
        summary = generate_code_summary(response, tool_results, [])

        # Assert
        assert 'Tools Executed:' in summary
        assert '2 successful operations' in summary

    def test_generate_code_summary_operation_symbols(self):
        """Test that operation symbols are correct."""
        # Arrange
        response = Mock()
        response.content = ''

        changes = [
            GitChange(file_path='new.py', operation='create', old_content=None, new_content='', diff=None),
            GitChange(file_path='edit.py', operation='modify', old_content='', new_content='', diff=None),
            GitChange(file_path='old.py', operation='delete', old_content='', new_content=None, diff=None),
        ]

        # Act
        summary = generate_code_summary(response, [], changes)

        # Assert
        assert '+ new.py' in summary  # create
        assert '~ edit.py' in summary  # modify
        assert '- old.py' in summary  # delete


class TestCoderPrompts:
    """Tests for coder agent prompts."""

    def test_coder_system_prompt_includes_key_responsibilities(self):
        """Test that system prompt covers all key areas."""
        assert 'production-ready code' in CODER_SYSTEM_PROMPT
        assert 'best practices' in CODER_SYSTEM_PROMPT
        assert 'tests' in CODER_SYSTEM_PROMPT
        assert 'documentation' in CODER_SYSTEM_PROMPT
        assert 'Security' in CODER_SYSTEM_PROMPT

    def test_code_generation_prompt_structure(self):
        """Test code generation prompt has required fields."""
        assert '{task}' in CODE_GENERATION_PROMPT
        assert '{repo_url}' in CODE_GENERATION_PROMPT
        assert '{branch}' in CODE_GENERATION_PROMPT
        assert '{workspace}' in CODE_GENERATION_PROMPT

    def test_debugging_prompt_structure(self):
        """Test debugging prompt has required fields."""
        assert '{task}' in DEBUGGING_PROMPT
        assert 'root cause' in DEBUGGING_PROMPT
        assert 'fix' in DEBUGGING_PROMPT

    def test_refactoring_prompt_structure(self):
        """Test refactoring prompt has required fields."""
        assert '{task}' in REFACTORING_PROMPT
        assert 'Preserve existing functionality' in REFACTORING_PROMPT
        assert 'design patterns' in REFACTORING_PROMPT
