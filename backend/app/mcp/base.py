"""
Base MCP client interface and error classes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class MCPTimeoutError(MCPError):
    """Raised when an MCP request times out."""

    pass


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    pass


class MCPAuthenticationError(MCPError):
    """Raised when authentication with MCP server fails."""

    pass


class MCPToolNotFoundError(MCPError):
    """Raised when requested MCP tool doesn't exist."""

    pass


class BaseMCPClient(ABC):
    """
    Abstract base class for MCP clients.

    All MCP clients (GitHub, Figma, Slack) inherit from this and implement
    the protocol-specific communication logic.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize MCP client.

        Args:
            server_url: URL of the remote MCP server (if applicable)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.server_url = server_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._connected = False
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._last_cache_update: Optional[datetime] = None

    @property
    @abstractmethod
    def server_type(self) -> str:
        """Return the server type identifier (e.g., 'github', 'figma', 'slack')."""
        pass

    @abstractmethod
    async def connect(self, auth_token: Optional[str] = None) -> None:
        """
        Establish connection to the MCP server.

        Args:
            auth_token: Authentication token for the MCP server

        Raises:
            MCPConnectionError: If connection fails
            MCPAuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        pass

    @abstractmethod
    async def list_tools(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        List all available tools from the MCP server.

        Args:
            refresh: Force refresh of tools cache

        Returns:
            List of tool definitions with name, description, and input schema

        Example response:
            [
                {
                    "name": "create_issue",
                    "description": "Create a new GitHub issue",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string"},
                            "title": {"type": "string"},
                            "body": {"type": "string"}
                        },
                        "required": ["repo", "title"]
                    }
                }
            ]
        """
        pass

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call a specific MCP tool with provided arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary
            auth_token: Authentication token (if required)

        Returns:
            Tool execution result

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
            MCPError: If tool execution fails
            MCPTimeoutError: If request times out
        """
        pass

    async def validate_tool_arguments(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> bool:
        """
        Validate tool arguments against the tool's input schema.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate

        Returns:
            True if valid, False otherwise

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
        """
        tools = await self.list_tools()
        tool = next((t for t in tools if t["name"] == tool_name), None)

        if not tool:
            raise MCPToolNotFoundError(f"Tool '{tool_name}' not found on {self.server_type} server")

        # Basic validation - can be enhanced with jsonschema
        input_schema = tool.get("inputSchema", {})
        required = input_schema.get("required", [])

        # Check all required fields are present
        for field in required:
            if field not in arguments:
                logger.warning(f"Missing required field '{field}' for tool '{tool_name}'")
                return False

        return True

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to the MCP server."""
        return self._connected

    def _update_tools_cache(self, tools: List[Dict[str, Any]]) -> None:
        """Update the internal tools cache."""
        self._tools_cache = tools
        self._last_cache_update = datetime.utcnow()
        logger.debug(f"Updated tools cache for {self.server_type} with {len(tools)} tools")
