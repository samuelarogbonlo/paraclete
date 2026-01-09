"""
GitHub MCP client implementation.

Connects to the official GitHub MCP server (github/github-mcp-server).
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


class GitHubMCPClient(BaseMCPClient):
    """
    Client for GitHub MCP server operations.

    Supports repository operations, PR management, issues, and code search.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize GitHub MCP client.

        Args:
            server_url: URL of the GitHub MCP server (if using remote)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        super().__init__(server_url=server_url, timeout=timeout, max_retries=max_retries)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def server_type(self) -> str:
        """Return server type identifier."""
        return "github"

    async def connect(self, auth_token: Optional[str] = None) -> None:
        """
        Establish connection to GitHub MCP server.

        Args:
            auth_token: GitHub personal access token

        Raises:
            MCPConnectionError: If connection fails
            MCPAuthenticationError: If authentication fails
        """
        if not auth_token:
            raise MCPAuthenticationError("GitHub token is required")

        try:
            # Initialize HTTP client with auth headers
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Accept": "application/json",
                    "User-Agent": "Paraclete-MCP-Client/1.0",
                },
            )

            # Test connection by listing tools
            if self.server_url:
                # For remote MCP server
                response = await self._http_client.get(f"{self.server_url}/tools")
                response.raise_for_status()
                tools = response.json()
            else:
                # Direct GitHub API for tool discovery
                tools = self._get_builtin_tools()

            self._update_tools_cache(tools)
            self._connected = True
            logger.info("Connected to GitHub MCP server")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MCPAuthenticationError("Invalid GitHub token")
            raise MCPConnectionError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            raise MCPConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise MCPConnectionError(f"Unexpected error: {e}")

    async def disconnect(self) -> None:
        """Close connection to GitHub MCP server."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False
        logger.info("Disconnected from GitHub MCP server")

    async def list_tools(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        List all available GitHub MCP tools.

        Args:
            refresh: Force refresh of tools cache

        Returns:
            List of tool definitions
        """
        # Return cached tools if available and not expired
        if (
            not refresh
            and self._tools_cache
            and self._last_cache_update
            and datetime.utcnow() - self._last_cache_update < timedelta(hours=1)
        ):
            return self._tools_cache

        if not self._connected:
            raise MCPConnectionError("Not connected to GitHub MCP server")

        if self.server_url and self._http_client:
            # Fetch from remote MCP server
            response = await self._http_client.get(f"{self.server_url}/tools")
            response.raise_for_status()
            tools = response.json()
        else:
            # Return built-in tool definitions
            tools = self._get_builtin_tools()

        self._update_tools_cache(tools)
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call a GitHub MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            auth_token: GitHub token (uses connection token if not provided)

        Returns:
            Tool execution result

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
            MCPError: If tool execution fails
            MCPTimeoutError: If request times out
        """
        if not self._connected:
            raise MCPConnectionError("Not connected to GitHub MCP server")

        # Validate arguments
        await self.validate_tool_arguments(tool_name, arguments)

        try:
            if self.server_url and self._http_client:
                # Call remote MCP server
                response = await self._http_client.post(
                    f"{self.server_url}/tools/{tool_name}",
                    json={"arguments": arguments},
                )
                response.raise_for_status()
                return response.json()
            else:
                # Execute tool directly via GitHub API
                return await self._execute_builtin_tool(tool_name, arguments)

        except httpx.TimeoutException:
            raise MCPTimeoutError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MCPToolNotFoundError(f"Tool '{tool_name}' not found")
            raise MCPError(f"Tool execution failed: {e.response.text}")
        except Exception as e:
            raise MCPError(f"Unexpected error calling tool: {e}")

    def _get_builtin_tools(self) -> List[Dict[str, Any]]:
        """
        Get built-in GitHub tool definitions.

        These match the tools provided by github/github-mcp-server.
        """
        return [
            {
                "name": "create_repository",
                "description": "Create a new GitHub repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Repository name"},
                        "description": {
                            "type": "string",
                            "description": "Repository description",
                        },
                        "private": {
                            "type": "boolean",
                            "description": "Whether the repository is private",
                            "default": False,
                        },
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "create_issue",
                "description": "Create a new issue in a repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in format 'owner/repo'",
                        },
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body"},
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Issue labels",
                        },
                    },
                    "required": ["repo", "title"],
                },
            },
            {
                "name": "create_pull_request",
                "description": "Create a new pull request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in format 'owner/repo'",
                        },
                        "title": {"type": "string", "description": "PR title"},
                        "body": {"type": "string", "description": "PR description"},
                        "head": {"type": "string", "description": "Head branch name"},
                        "base": {
                            "type": "string",
                            "description": "Base branch name",
                            "default": "main",
                        },
                    },
                    "required": ["repo", "title", "head"],
                },
            },
            {
                "name": "get_file_contents",
                "description": "Get contents of a file from a repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in format 'owner/repo'",
                        },
                        "path": {"type": "string", "description": "File path"},
                        "branch": {
                            "type": "string",
                            "description": "Branch name",
                            "default": "main",
                        },
                    },
                    "required": ["repo", "path"],
                },
            },
            {
                "name": "search_code",
                "description": "Search code in repositories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "repo": {
                            "type": "string",
                            "description": "Optional repository to limit search",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_pull_requests",
                "description": "List pull requests for a repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in format 'owner/repo'",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "default": "open",
                        },
                    },
                    "required": ["repo"],
                },
            },
        ]

    async def _execute_builtin_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tool directly via GitHub API.

        This is used when not connected to a remote MCP server.
        """
        if not self._http_client:
            raise MCPConnectionError("HTTP client not initialized")

        # Map tool calls to GitHub API endpoints
        github_api_base = "https://api.github.com"

        if tool_name == "create_repository":
            response = await self._http_client.post(
                f"{github_api_base}/user/repos",
                json={
                    "name": arguments["name"],
                    "description": arguments.get("description", ""),
                    "private": arguments.get("private", False),
                },
            )
            response.raise_for_status()
            return response.json()

        elif tool_name == "create_issue":
            repo = arguments["repo"]
            response = await self._http_client.post(
                f"{github_api_base}/repos/{repo}/issues",
                json={
                    "title": arguments["title"],
                    "body": arguments.get("body", ""),
                    "labels": arguments.get("labels", []),
                },
            )
            response.raise_for_status()
            return response.json()

        elif tool_name == "create_pull_request":
            repo = arguments["repo"]
            response = await self._http_client.post(
                f"{github_api_base}/repos/{repo}/pulls",
                json={
                    "title": arguments["title"],
                    "body": arguments.get("body", ""),
                    "head": arguments["head"],
                    "base": arguments.get("base", "main"),
                },
            )
            response.raise_for_status()
            return response.json()

        elif tool_name == "get_file_contents":
            repo = arguments["repo"]
            path = arguments["path"]
            branch = arguments.get("branch", "main")
            response = await self._http_client.get(
                f"{github_api_base}/repos/{repo}/contents/{path}",
                params={"ref": branch},
            )
            response.raise_for_status()
            return response.json()

        elif tool_name == "search_code":
            query = arguments["query"]
            if "repo" in arguments:
                query = f"{query} repo:{arguments['repo']}"
            response = await self._http_client.get(
                f"{github_api_base}/search/code", params={"q": query}
            )
            response.raise_for_status()
            return response.json()

        elif tool_name == "list_pull_requests":
            repo = arguments["repo"]
            state = arguments.get("state", "open")
            response = await self._http_client.get(
                f"{github_api_base}/repos/{repo}/pulls", params={"state": state}
            )
            response.raise_for_status()
            return response.json()

        else:
            raise MCPToolNotFoundError(f"Unknown tool: {tool_name}")
