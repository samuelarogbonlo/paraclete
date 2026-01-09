"""
Tests for GitHub MCP client.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.mcp.clients.github import GitHubMCPClient
from app.mcp.base import (
    MCPConnectionError,
    MCPAuthenticationError,
    MCPToolNotFoundError,
)


@pytest.fixture
def github_client():
    """Create GitHub MCP client instance."""
    return GitHubMCPClient(timeout=5, max_retries=2)


@pytest.mark.asyncio
async def test_github_client_initialization(github_client):
    """Test GitHub client initialization."""
    assert github_client.server_type == "github"
    assert github_client.timeout == 5
    assert github_client.max_retries == 2
    assert not github_client.is_connected


@pytest.mark.asyncio
async def test_github_connect_success(github_client):
    """Test successful connection to GitHub MCP."""
    with patch.object(github_client, "_http_client", new=AsyncMock()) as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.get.return_value = mock_response

        # Set server_url for remote MCP mode
        github_client.server_url = "http://test-mcp-server"

        await github_client.connect(auth_token="test_token")

        assert github_client.is_connected
        assert github_client._tools_cache is not None


@pytest.mark.asyncio
async def test_github_connect_no_token(github_client):
    """Test connection without auth token fails."""
    with pytest.raises(MCPAuthenticationError):
        await github_client.connect(auth_token=None)


@pytest.mark.asyncio
async def test_list_tools(github_client):
    """Test listing GitHub tools."""
    # Connect first
    github_client._connected = True
    github_client._http_client = AsyncMock()

    tools = await github_client.list_tools()

    # Should return built-in tools
    assert len(tools) > 0
    assert any(t["name"] == "create_repository" for t in tools)
    assert any(t["name"] == "create_issue" for t in tools)
    assert any(t["name"] == "create_pull_request" for t in tools)


@pytest.mark.asyncio
async def test_call_tool_not_connected(github_client):
    """Test calling tool when not connected fails."""
    with pytest.raises(MCPConnectionError):
        await github_client.call_tool(
            tool_name="create_repository",
            arguments={"name": "test-repo"},
        )


@pytest.mark.asyncio
async def test_validate_tool_arguments(github_client):
    """Test tool argument validation."""
    github_client._connected = True
    github_client._http_client = AsyncMock()

    # Valid arguments
    is_valid = await github_client.validate_tool_arguments(
        tool_name="create_repository",
        arguments={"name": "test-repo"},
    )
    assert is_valid

    # Missing required argument
    is_valid = await github_client.validate_tool_arguments(
        tool_name="create_repository",
        arguments={},
    )
    assert not is_valid


@pytest.mark.asyncio
async def test_disconnect(github_client):
    """Test disconnecting from GitHub MCP."""
    github_client._connected = True
    github_client._http_client = AsyncMock()

    await github_client.disconnect()

    assert not github_client.is_connected
    assert github_client._http_client is None
