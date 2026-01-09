"""
MCP client implementations for various integrations.
"""

from app.mcp.clients.github import GitHubMCPClient
from app.mcp.clients.figma import FigmaMCPClient
from app.mcp.clients.slack import SlackMCPClient

__all__ = [
    "GitHubMCPClient",
    "FigmaMCPClient",
    "SlackMCPClient",
]
