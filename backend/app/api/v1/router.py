"""
Main API v1 router.
"""
from fastapi import APIRouter

from app.api.v1 import sessions, agents, voice, mcp, compute

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(agents.router, prefix="/sessions", tags=["Agents"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice"])
api_router.include_router(mcp.router, tags=["MCP"])
api_router.include_router(compute.router, tags=["Compute"])