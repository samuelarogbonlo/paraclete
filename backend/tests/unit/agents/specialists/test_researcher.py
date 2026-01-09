"""
Test suite for the researcher specialist agent.

Tests web search and documentation lookup workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from app.agents.specialists.researcher import (
    researcher_node,
    RESEARCHER_SYSTEM_PROMPT,
    research_with_context,
)
from app.agents.state import AgentState, AgentOutput


@pytest.fixture
def mock_model_router():
    """Mock ModelRouter for testing."""
    with patch('app.agents.specialists.researcher.ModelRouter') as mock_router:
        mock_instance = Mock()
        mock_model = Mock()
        mock_model.model_name = 'gemini-1.5-pro'
        mock_model.bind_tools = Mock(return_value=mock_model)
        mock_instance.get_model = Mock(return_value=mock_model)
        mock_router.return_value = mock_instance
        yield mock_router


@pytest.fixture
def mock_search_tools():
    """Mock search tools."""
    with patch('app.agents.specialists.researcher.get_search_tools') as mock:
        tool1 = Mock(name='web_search')
        tool1.name = 'web_search'
        tool1.invoke = Mock(return_value={
            'results': [
                {'title': 'Result 1', 'url': 'http://example.com/1', 'snippet': 'Info 1'},
                {'title': 'Result 2', 'url': 'http://example.com/2', 'snippet': 'Info 2'},
            ]
        })

        tool2 = Mock(name='github_search')
        tool2.name = 'github_search'
        tool2.invoke = Mock(return_value={
            'repositories': [
                {'name': 'repo1', 'url': 'https://github.com/user/repo1'},
            ]
        })

        mock.return_value = [tool1, tool2]
        yield mock


@pytest.fixture
def base_state():
    """Base agent state for testing."""
    return {
        'session_id': 'test-session-123',
        'messages': [HumanMessage(content='Research best practices for FastAPI testing')],
        'task_description': 'Research best practices for FastAPI testing',
        'google_api_key': 'test-google-key',
        'github_token': 'test-github-token',
        'agent_outputs': [],
        'agent_statuses': {},
    }


class TestResearcherNode:
    """Tests for the researcher_node function."""

    def test_researcher_node_basic_execution(self, mock_model_router, mock_search_tools, base_state):
        """Test basic researcher agent execution."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research findings on FastAPI testing'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = researcher_node(base_state)

        # Assert
        assert isinstance(result, Command)
        assert 'messages' in result.update
        assert len(result.update['messages']) > 0
        assert isinstance(result.update['messages'][0], AIMessage)
        assert result.update['agent_statuses']['researcher'] == 'completed'

    def test_researcher_node_uses_gemini_model(self, mock_model_router, mock_search_tools, base_state):
        """Test that researcher agent uses Gemini model for large context."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        researcher_node(base_state)

        # Assert
        from app.agents.router import AgentType
        mock_model_router.return_value.get_model.assert_called_with(
            AgentType.RESEARCHER,
            context_size=100000,  # Large context for research
        )

    def test_researcher_node_binds_search_tools(self, mock_model_router, mock_search_tools, base_state):
        """Test that researcher agent binds search tools."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        researcher_node(base_state)

        # Assert
        mock_search_tools.assert_called_once_with(
            google_api_key='test-google-key',
            github_token='test-github-token',
        )
        mock_model.bind_tools.assert_called_once()

    def test_researcher_node_with_tool_calls(self, mock_model_router, mock_search_tools, base_state):
        """Test researcher agent execution with tool calls."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Searching web...'
        mock_response.tool_calls = [
            {
                'name': 'web_search',
                'args': {
                    'query': 'FastAPI testing best practices',
                    'num_results': 5,
                }
            }
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = researcher_node(base_state)

        # Assert
        assert 'search_results' in result.update
        assert len(result.update['search_results']) > 0

    def test_researcher_node_generates_summary_from_tool_results(self, mock_model_router, mock_search_tools, base_state):
        """Test that researcher generates summary from search results."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value

        # First call - with tool calls
        search_response = Mock()
        search_response.content = 'Searching...'
        search_response.tool_calls = [
            {'name': 'web_search', 'args': {'query': 'test'}}
        ]

        # Second call - summary generation
        summary_response = Mock()
        summary_response.content = 'Comprehensive research summary with citations'

        mock_model.invoke = Mock(side_effect=[search_response, summary_response])

        # Act
        result = researcher_node(base_state)

        # Assert
        assert 'research_summary' in result.update
        assert result.update['research_summary'] == 'Comprehensive research summary with citations'

    def test_researcher_node_routes_to_end_when_complete(self, mock_model_router, mock_search_tools, base_state):
        """Test routing to END when research is complete."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['requires_approval'] = False

        # Act
        result = researcher_node(base_state)

        # Assert
        assert result.goto == 'END'

    def test_researcher_node_routes_to_approval_when_required(self, mock_model_router, mock_search_tools, base_state):
        """Test routing to approval when required."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['requires_approval'] = True

        # Act
        result = researcher_node(base_state)

        # Assert
        assert result.goto == 'approval'

    def test_researcher_node_routes_to_aggregator_for_subtasks(self, mock_model_router, mock_search_tools, base_state):
        """Test routing to result aggregator when subtasks exist."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['subtasks'] = ['task1', 'task2']
        base_state['completed_subtasks'] = ['task1']  # Still has task2 pending

        # Act
        result = researcher_node(base_state)

        # Assert
        assert result.goto == 'result_aggregator'

    def test_researcher_node_handles_errors_gracefully(self, mock_model_router, mock_search_tools, base_state):
        """Test error handling in researcher agent."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_model.invoke = Mock(side_effect=Exception('Search API error'))

        # Act
        result = researcher_node(base_state)

        # Assert
        assert result.goto == 'error_handler'
        assert 'errors' in result.update
        assert len(result.update['errors']) > 0
        assert result.update['agent_statuses']['researcher'] == 'failed'

    def test_researcher_node_creates_agent_output(self, mock_model_router, mock_search_tools, base_state):
        """Test that agent output is created correctly."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research findings'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = researcher_node(base_state)

        # Assert
        outputs = result.update['agent_outputs']
        assert len(outputs) > 0

        output = outputs[-1]
        assert output['agent_name'] == 'researcher'
        assert output['model_used'] == 'gemini-1.5-pro'
        assert output['error'] is None
        assert 'summary' in output['result']
        assert 'sources' in output['result']
        assert 'task' in output['result']

    def test_researcher_node_uses_task_from_messages_when_not_specified(self, mock_model_router, mock_search_tools, base_state):
        """Test extracting task from messages when task_description is empty."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Research complete'
        mock_response.tool_calls = []
        mock_model.invoke = Mock(return_value=mock_response)

        base_state['task_description'] = ''
        base_state['messages'] = [HumanMessage(content='Find information about GraphQL')]

        # Act
        result = researcher_node(base_state)

        # Assert
        output = result.update['agent_outputs'][-1]
        assert output['result']['task'] == 'Find information about GraphQL'

    def test_researcher_node_includes_sources_in_output(self, mock_model_router, mock_search_tools, base_state):
        """Test that sources are included in research output."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value

        search_response = Mock()
        search_response.content = 'Searching...'
        search_response.tool_calls = [
            {'name': 'web_search', 'args': {'query': 'test'}}
        ]

        summary_response = Mock()
        summary_response.content = 'Summary'

        mock_model.invoke = Mock(side_effect=[search_response, summary_response])

        # Act
        result = researcher_node(base_state)

        # Assert
        output = result.update['agent_outputs'][-1]
        assert 'sources' in output['result']
        assert isinstance(output['result']['sources'], list)

    def test_researcher_node_handles_multiple_tool_calls(self, mock_model_router, mock_search_tools, base_state):
        """Test handling multiple tool calls."""
        # Arrange
        mock_model = mock_model_router.return_value.get_model.return_value
        mock_response = Mock()
        mock_response.content = 'Multiple searches'
        mock_response.tool_calls = [
            {'name': 'web_search', 'args': {'query': 'query1'}},
            {'name': 'github_search', 'args': {'query': 'repo1'}},
            {'name': 'web_search', 'args': {'query': 'query2'}},
        ]
        mock_model.invoke = Mock(return_value=mock_response)

        # Act
        result = researcher_node(base_state)

        # Assert
        assert len(result.update['search_results']) == 3


class TestResearchWithContext:
    """Tests for research_with_context helper function."""

    def test_research_with_context_performs_iterative_search(self):
        """Test that research_with_context performs iterative searches."""
        # Arrange
        mock_model = Mock()
        mock_model.invoke = Mock(return_value=Mock(content='Follow-up query'))

        mock_tool = Mock()
        mock_tool.name = 'web_search'
        mock_tool.invoke = Mock(return_value={'results': []})

        # Act
        result = research_with_context(
            query='Initial query',
            context=[],
            model=mock_model,
            search_tools=[mock_tool],
            max_searches=3,
        )

        # Assert
        assert 'query' in result
        assert 'iterations' in result
        assert 'results' in result
        assert result['iterations'] > 0

    def test_research_with_context_respects_max_searches(self):
        """Test that max_searches limit is respected."""
        # Arrange
        mock_model = Mock()
        mock_model.invoke = Mock(return_value=Mock(content='More queries'))

        mock_tool = Mock()
        mock_tool.name = 'web_search'
        mock_tool.invoke = Mock(return_value={'results': []})

        # Act
        result = research_with_context(
            query='Test query',
            context=[],
            model=mock_model,
            search_tools=[mock_tool],
            max_searches=2,
        )

        # Assert
        assert result['iterations'] <= 2

    def test_research_with_context_builds_context(self):
        """Test that context is built from results."""
        # Arrange
        mock_model = Mock()
        mock_model.invoke = Mock(return_value=Mock(content=''))

        mock_tool = Mock()
        mock_tool.name = 'web_search'
        mock_tool.invoke = Mock(return_value={'results': ['result1', 'result2']})

        initial_context = ['Previous research']

        # Act
        result = research_with_context(
            query='Test query',
            context=initial_context,
            model=mock_model,
            search_tools=[mock_tool],
            max_searches=1,
        )

        # Assert
        assert 'context' in result
        assert result['context'] == initial_context

    def test_research_with_context_handles_no_follow_up_queries(self):
        """Test handling when no follow-up queries are generated."""
        # Arrange
        mock_model = Mock()
        mock_model.invoke = Mock(return_value=Mock(content=''))

        mock_tool = Mock()
        mock_tool.name = 'web_search'
        mock_tool.invoke = Mock(return_value={'results': []})

        # Act
        result = research_with_context(
            query='Test query',
            context=[],
            model=mock_model,
            search_tools=[mock_tool],
            max_searches=3,
        )

        # Assert
        assert result['iterations'] == 1  # Only initial search

    def test_research_with_context_uses_correct_tool(self):
        """Test that the correct search tool is used."""
        # Arrange
        mock_model = Mock()
        mock_model.invoke = Mock(return_value=Mock(content=''))

        mock_tool = Mock()
        mock_tool.name = 'web_search'
        mock_tool.invoke = Mock(return_value={'results': []})

        other_tool = Mock()
        other_tool.name = 'other_search'

        # Act
        research_with_context(
            query='Test query',
            context=[],
            model=mock_model,
            search_tools=[other_tool, mock_tool],
            max_searches=1,
        )

        # Assert
        mock_tool.invoke.assert_called_once()
        other_tool.invoke.assert_not_called()


class TestResearcherPrompts:
    """Tests for researcher agent prompts."""

    def test_researcher_system_prompt_includes_key_responsibilities(self):
        """Test that system prompt covers all key areas."""
        assert 'research specialist' in RESEARCHER_SYSTEM_PROMPT
        assert 'Search for relevant information' in RESEARCHER_SYSTEM_PROMPT
        assert 'Synthesize findings' in RESEARCHER_SYSTEM_PROMPT
        assert 'sources and citations' in RESEARCHER_SYSTEM_PROMPT
        assert 'accuracy' in RESEARCHER_SYSTEM_PROMPT

    def test_researcher_system_prompt_emphasizes_citations(self):
        """Test that prompt emphasizes citation requirements."""
        assert 'cite your sources' in RESEARCHER_SYSTEM_PROMPT.lower()
        assert 'sources' in RESEARCHER_SYSTEM_PROMPT.lower()
