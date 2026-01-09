"""
Tests for MCP Proxy Server.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.mcp.proxy import MCPProxyServer
from app.mcp.base import MCPToolNotFoundError, MCPError


@pytest.fixture
async def proxy_server():
    """Create MCP proxy server instance."""
    proxy = MCPProxyServer()
    await proxy.initialize()
    return proxy


@pytest.mark.asyncio
async def test_proxy_initialization(proxy_server):
    """Test proxy server initialization."""
    assert proxy_server._initialized
    assert "github" in proxy_server._clients
    assert "figma" in proxy_server._clients
    assert "slack" in proxy_server._clients


@pytest.mark.asyncio
async def test_list_servers(proxy_server):
    """Test listing available MCP servers."""
    servers = await proxy_server.list_servers()

    assert len(servers) == 3
    server_types = [s["server_type"] for s in servers]
    assert "github" in server_types
    assert "figma" in server_types
    assert "slack" in server_types


@pytest.mark.asyncio
async def test_health_check(proxy_server):
    """Test health check endpoint."""
    health = await proxy_server.health_check()

    assert "status" in health
    assert "clients" in health
    assert "timestamp" in health
    assert len(health["clients"]) == 3


@pytest.mark.asyncio
async def test_get_client_invalid_server():
    """Test getting client with invalid server type."""
    proxy = MCPProxyServer()
    await proxy.initialize()

    with pytest.raises(ValueError):
        async with proxy.get_client("invalid_server", "test_token"):
            pass


@pytest.mark.asyncio
async def test_execute_tool_retry_logic(proxy_server):
    """Test that execute_tool retries on failure."""
    with patch.object(
        proxy_server._clients["github"], "call_tool"
    ) as mock_call_tool:
        # Fail twice, then succeed
        mock_call_tool.side_effect = [
            MCPError("Temporary error"),
            MCPError("Another error"),
            {"result": "success"},
        ]

        # Should succeed after retries
        result = await proxy_server.execute_tool(
            server_type="github",
            tool_name="test_tool",
            arguments={},
            auth_token="test_token",
        )

        assert result == {"result": "success"}
        assert mock_call_tool.call_count == 3


@pytest.mark.asyncio
async def test_execute_tool_no_retry_on_tool_not_found(proxy_server):
    """Test that execute_tool doesn't retry if tool not found."""
    with patch.object(
        proxy_server._clients["github"], "call_tool"
    ) as mock_call_tool:
        mock_call_tool.side_effect = MCPToolNotFoundError("Tool not found")

        with pytest.raises(MCPToolNotFoundError):
            await proxy_server.execute_tool(
                server_type="github",
                tool_name="nonexistent_tool",
                arguments={},
                auth_token="test_token",
            )

        # Should only call once (no retries for tool not found)
        assert mock_call_tool.call_count == 1


@pytest.mark.asyncio
async def test_shutdown(proxy_server):
    """Test proxy server shutdown."""
    # Mock connected clients
    for client in proxy_server._clients.values():
        client._connected = True
        client.disconnect = AsyncMock()

    await proxy_server.shutdown()

    # Verify all clients were disconnected
    for client in proxy_server._clients.values():
        if client.disconnect.called:
            client.disconnect.assert_called_once()
