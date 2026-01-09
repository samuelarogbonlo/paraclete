"""
MCP (Model Context Protocol) proxy server and clients.

This module provides a unified interface for interacting with remote MCP servers
for GitHub, Figma, Slack, and other integrations.
"""

from app.mcp.proxy import MCPProxyServer
from app.mcp.base import BaseMCPClient, MCPError, MCPTimeoutError, MCPConnectionError

__all__ = [
    "MCPProxyServer",
    "BaseMCPClient",
    "MCPError",
    "MCPTimeoutError",
    "MCPConnectionError",
]
