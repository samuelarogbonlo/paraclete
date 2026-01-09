"""
Figma MCP client implementation.

Connects to Figma's official MCP server for design operations.
"""

from typing import Any, Dict, List, Optional
import httpx
import logging
from datetime import datetime, timedelta

from app.mcp.base import (
    BaseMCPClient,
    MCPError,
    MCPTimeoutError,
    MCPConnectionError,
    MCPAuthenticationError,
    MCPToolNotFoundError,
)

logger = logging.getLogger(__name__)


class FigmaMCPClient(BaseMCPClient):
    """
    Client for Figma MCP server operations.

    Supports design file access, component extraction, and collaboration features.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Figma MCP client.

        Args:
            server_url: URL of the Figma MCP server
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        super().__init__(server_url=server_url, timeout=timeout, max_retries=max_retries)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def server_type(self) -> str:
        """Return server type identifier."""
        return "figma"

    async def connect(self, auth_token: Optional[str] = None) -> None:
        """
        Establish connection to Figma MCP server.

        Args:
            auth_token: Figma personal access token

        Raises:
            MCPConnectionError: If connection fails
            MCPAuthenticationError: If authentication fails
        """
        if not auth_token:
            raise MCPAuthenticationError("Figma token is required")

        if not self.server_url:
            raise MCPConnectionError("Figma MCP server URL is required")

        try:
            # Initialize HTTP client
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Accept": "application/json",
                },
            )

            # Test connection
            response = await self._http_client.get(f"{self.server_url}/tools")
            response.raise_for_status()
            tools = response.json()

            self._update_tools_cache(tools)
            self._connected = True
            logger.info("Connected to Figma MCP server")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MCPAuthenticationError("Invalid Figma token")
            raise MCPConnectionError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            raise MCPConnectionError(f"Connection error: {e}")

    async def disconnect(self) -> None:
        """Close connection to Figma MCP server."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False
        logger.info("Disconnected from Figma MCP server")

    async def list_tools(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        List all available Figma MCP tools.

        Args:
            refresh: Force refresh of tools cache

        Returns:
            List of tool definitions
        """
        # Return cached tools if available
        if (
            not refresh
            and self._tools_cache
            and self._last_cache_update
            and datetime.utcnow() - self._last_cache_update < timedelta(hours=1)
        ):
            return self._tools_cache

        if not self._connected or not self._http_client:
            raise MCPConnectionError("Not connected to Figma MCP server")

        response = await self._http_client.get(f"{self.server_url}/tools")
        response.raise_for_status()
        tools = response.json()

        self._update_tools_cache(tools)
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call a Figma MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            auth_token: Figma token (optional, uses connection token)

        Returns:
            Tool execution result

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
            MCPError: If tool execution fails
            MCPTimeoutError: If request times out
        """
        if not self._connected or not self._http_client:
            raise MCPConnectionError("Not connected to Figma MCP server")

        # Validate arguments
        await self.validate_tool_arguments(tool_name, arguments)

        try:
            response = await self._http_client.post(
                f"{self.server_url}/tools/{tool_name}",
                json={"arguments": arguments},
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise MCPTimeoutError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MCPToolNotFoundError(f"Tool '{tool_name}' not found")
            raise MCPError(f"Tool execution failed: {e.response.text}")
        except Exception as e:
            raise MCPError(f"Unexpected error calling tool: {e}")
