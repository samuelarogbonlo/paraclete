"""
MCP Proxy Server for routing requests to remote MCP servers.

Provides a unified interface for all MCP operations with connection pooling,
authentication passthrough, and error handling.
"""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from app.mcp.clients import GitHubMCPClient, FigmaMCPClient, SlackMCPClient
from app.mcp.base import (
    BaseMCPClient,
    MCPError,
    MCPToolNotFoundError,
    MCPConnectionError,
)
from app.config import settings

logger = logging.getLogger(__name__)


class MCPProxyServer:
    """
    Central proxy server for routing MCP requests to appropriate clients.

    Features:
    - Connection pooling for efficient resource usage
    - Authentication token passthrough
    - Request/response transformation
    - Error handling and retries
    - Health monitoring
    """

    def __init__(self):
        """Initialize MCP proxy server."""
        self._clients: Dict[str, BaseMCPClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all MCP clients."""
        if self._initialized:
            return

        # Initialize client instances (connections happen per-request with user tokens)
        self._clients = {
            "github": GitHubMCPClient(
                server_url=settings.MCP_GITHUB_SERVER_URL,
                timeout=settings.MCP_REQUEST_TIMEOUT_SECONDS,
                max_retries=settings.MCP_MAX_RETRIES,
            ),
            "figma": FigmaMCPClient(
                server_url=settings.MCP_FIGMA_SERVER_URL,
                timeout=settings.MCP_REQUEST_TIMEOUT_SECONDS,
                max_retries=settings.MCP_MAX_RETRIES,
            ),
            "slack": SlackMCPClient(
                server_url=settings.MCP_SLACK_SERVER_URL,
                timeout=settings.MCP_REQUEST_TIMEOUT_SECONDS,
                max_retries=settings.MCP_MAX_RETRIES,
            ),
        }

        # Initialize locks for thread-safe operations
        for server_type in self._clients.keys():
            self._client_locks[server_type] = asyncio.Lock()

        self._initialized = True
        logger.info(f"MCP Proxy Server initialized with {len(self._clients)} clients")

    async def shutdown(self) -> None:
        """Shutdown all MCP clients."""
        for client in self._clients.values():
            if client.is_connected:
                await client.disconnect()
        logger.info("MCP Proxy Server shutdown complete")

    @asynccontextmanager
    async def get_client(
        self, server_type: str, auth_token: str
    ) -> BaseMCPClient:
        """
        Get an MCP client with connection management.

        Args:
            server_type: Type of server ('github', 'figma', 'slack')
            auth_token: User's authentication token for the service

        Yields:
            Connected MCP client instance

        Raises:
            ValueError: If server_type is invalid
            MCPConnectionError: If connection fails
        """
        if server_type not in self._clients:
            raise ValueError(
                f"Invalid server type: {server_type}. "
                f"Must be one of: {list(self._clients.keys())}"
            )

        client = self._clients[server_type]
        lock = self._client_locks[server_type]

        async with lock:
            try:
                # Connect if not already connected
                if not client.is_connected:
                    await client.connect(auth_token=auth_token)

                yield client

            except Exception as e:
                logger.error(f"Error with {server_type} client: {e}")
                # Try to reconnect on next request
                try:
                    await client.disconnect()
                except:
                    pass
                raise

    async def list_servers(self) -> List[Dict[str, Any]]:
        """
        List all available MCP servers and their status.

        Returns:
            List of server information including available tools

        Example response:
            [
                {
                    "server_type": "github",
                    "status": "available",
                    "tools_count": 6,
                    "requires_auth": true
                },
                ...
            ]
        """
        servers = []

        for server_type, client in self._clients.items():
            server_info = {
                "server_type": server_type,
                "status": "connected" if client.is_connected else "available",
                "requires_auth": True,
            }

            # If connected, get tool count
            if client.is_connected:
                try:
                    tools = await client.list_tools()
                    server_info["tools_count"] = len(tools)
                except Exception as e:
                    logger.error(f"Error listing tools for {server_type}: {e}")
                    server_info["status"] = "error"
                    server_info["error"] = str(e)

            servers.append(server_info)

        return servers

    async def list_tools(
        self, server_type: str, auth_token: str, refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all tools available from a specific MCP server.

        Args:
            server_type: Type of server ('github', 'figma', 'slack')
            auth_token: User's authentication token
            refresh: Force refresh of tools cache

        Returns:
            List of tool definitions

        Raises:
            ValueError: If server_type is invalid
            MCPConnectionError: If connection fails
        """
        async with self.get_client(server_type, auth_token) as client:
            return await client.list_tools(refresh=refresh)

    async def execute_tool(
        self,
        server_type: str,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: str,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool with retry logic.

        Args:
            server_type: Type of server ('github', 'figma', 'slack')
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            auth_token: User's authentication token
            retry_count: Current retry attempt (internal)

        Returns:
            Tool execution result

        Raises:
            ValueError: If server_type is invalid
            MCPToolNotFoundError: If tool doesn't exist
            MCPError: If execution fails after all retries
        """
        try:
            async with self.get_client(server_type, auth_token) as client:
                result = await client.call_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    auth_token=auth_token,
                )

                logger.info(
                    f"Successfully executed {server_type}/{tool_name}"
                )
                return result

        except MCPToolNotFoundError:
            # Don't retry if tool doesn't exist
            raise

        except MCPError as e:
            # Retry on transient errors
            max_retries = settings.MCP_MAX_RETRIES
            if retry_count < max_retries:
                logger.warning(
                    f"Retrying {server_type}/{tool_name} "
                    f"(attempt {retry_count + 1}/{max_retries}): {e}"
                )
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self.execute_tool(
                    server_type=server_type,
                    tool_name=tool_name,
                    arguments=arguments,
                    auth_token=auth_token,
                    retry_count=retry_count + 1,
                )
            else:
                logger.error(
                    f"Failed to execute {server_type}/{tool_name} "
                    f"after {max_retries} retries: {e}"
                )
                raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all MCP clients.

        Returns:
            Health status for each client

        Example:
            {
                "status": "healthy",
                "clients": {
                    "github": {"status": "available", "connected": false},
                    "figma": {"status": "available", "connected": false},
                    "slack": {"status": "available", "connected": false}
                },
                "timestamp": "2026-01-07T12:00:00Z"
            }
        """
        clients_health = {}

        for server_type, client in self._clients.items():
            clients_health[server_type] = {
                "status": "available",
                "connected": client.is_connected,
            }

        # Overall status
        all_available = all(
            c["status"] == "available" for c in clients_health.values()
        )
        overall_status = "healthy" if all_available else "degraded"

        return {
            "status": overall_status,
            "clients": clients_health,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# Global proxy instance
_proxy_instance: Optional[MCPProxyServer] = None


async def get_mcp_proxy() -> MCPProxyServer:
    """
    Get the global MCP proxy instance.

    Returns:
        Initialized MCP proxy server
    """
    global _proxy_instance

    if _proxy_instance is None:
        _proxy_instance = MCPProxyServer()
        await _proxy_instance.initialize()

    return _proxy_instance
