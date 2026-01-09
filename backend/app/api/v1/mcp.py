"""
MCP API endpoints for tool invocation and server management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import User, MCPRequest, MCPRequestStatus, MCPServerType
from app.core.auth import get_current_user
from app.mcp.proxy import get_mcp_proxy
from app.mcp.base import MCPError, MCPToolNotFoundError, MCPConnectionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# Request/Response Models


class MCPToolExecuteRequest(BaseModel):
    """Request model for MCP tool execution."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    session_id: Optional[UUID] = Field(
        None, description="Optional session ID to link request"
    )


class MCPToolExecuteResponse(BaseModel):
    """Response model for MCP tool execution."""

    request_id: UUID = Field(..., description="Unique request ID")
    server_type: str = Field(..., description="MCP server type")
    tool_name: str = Field(..., description="Tool name")
    status: str = Field(..., description="Execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in ms")
    timestamp: datetime = Field(..., description="Request timestamp")


class MCPServerInfo(BaseModel):
    """Server information model."""

    server_type: str
    status: str
    tools_count: Optional[int] = None
    requires_auth: bool = True
    error: Optional[str] = None


class MCPToolDefinition(BaseModel):
    """Tool definition model."""

    name: str
    description: str
    inputSchema: Dict[str, Any]


# API Endpoints


@router.get("/servers", response_model=List[MCPServerInfo])
async def list_mcp_servers(
    current_user: User = Depends(get_current_user),
):
    """
    List all available MCP servers.

    Returns information about each server including status and tool count.
    """
    try:
        proxy = await get_mcp_proxy()
        servers = await proxy.list_servers()
        return servers

    except Exception as e:
        logger.error(f"Error listing MCP servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list MCP servers",
        )


@router.get("/{server_type}/tools", response_model=List[MCPToolDefinition])
async def list_server_tools(
    server_type: str,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
):
    """
    List all tools available from a specific MCP server.

    Args:
        server_type: Type of server ('github', 'figma', 'slack')
        refresh: Force refresh of tools cache
        x_auth_token: Service-specific auth token (GitHub token, Figma token, etc.)

    Returns:
        List of tool definitions
    """
    if not x_auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"X-Auth-Token header required for {server_type} operations",
        )

    try:
        proxy = await get_mcp_proxy()
        tools = await proxy.list_tools(
            server_type=server_type,
            auth_token=x_auth_token,
            refresh=refresh,
        )
        return tools

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to {server_type} MCP server: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error listing tools for {server_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tools",
        )


@router.post("/{server_type}/execute", response_model=MCPToolExecuteResponse)
async def execute_mcp_tool(
    server_type: str,
    request: MCPToolExecuteRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
):
    """
    Execute an MCP tool with provided arguments.

    Args:
        server_type: Type of server ('github', 'figma', 'slack')
        request: Tool execution request with name and arguments
        x_auth_token: Service-specific auth token

    Returns:
        Tool execution result
    """
    if not x_auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"X-Auth-Token header required for {server_type} operations",
        )

    # Map server_type string to enum
    server_type_enum = {
        "github": MCPServerType.GITHUB,
        "figma": MCPServerType.FIGMA,
        "slack": MCPServerType.SLACK,
    }.get(server_type.lower())

    if not server_type_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid server type: {server_type}",
        )

    # Create MCP request record
    mcp_request = MCPRequest(
        user_id=current_user.id,
        session_id=request.session_id,
        server_type=server_type_enum,
        tool_name=request.tool_name,
        arguments=request.arguments,
        status=MCPRequestStatus.PENDING,
    )
    db.add(mcp_request)
    await db.commit()
    await db.refresh(mcp_request)

    start_time = datetime.utcnow()

    try:
        # Execute tool via proxy
        proxy = await get_mcp_proxy()
        result = await proxy.execute_tool(
            server_type=server_type,
            tool_name=request.tool_name,
            arguments=request.arguments,
            auth_token=x_auth_token,
        )

        # Update request record with success
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        mcp_request.status = MCPRequestStatus.SUCCESS
        mcp_request.response = result
        mcp_request.duration_ms = duration_ms
        mcp_request.completed_at = end_time

        await db.commit()

        return MCPToolExecuteResponse(
            request_id=mcp_request.id,
            server_type=server_type,
            tool_name=request.tool_name,
            status="success",
            result=result,
            duration_ms=duration_ms,
            timestamp=mcp_request.requested_at,
        )

    except MCPToolNotFoundError as e:
        # Tool not found
        mcp_request.status = MCPRequestStatus.FAILED
        mcp_request.error_message = str(e)
        mcp_request.completed_at = datetime.utcnow()
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except MCPConnectionError as e:
        # Connection error
        mcp_request.status = MCPRequestStatus.FAILED
        mcp_request.error_message = str(e)
        mcp_request.completed_at = datetime.utcnow()
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to {server_type} server: {str(e)}",
        )

    except MCPError as e:
        # General MCP error
        mcp_request.status = MCPRequestStatus.FAILED
        mcp_request.error_message = str(e)
        mcp_request.completed_at = datetime.utcnow()
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error executing MCP tool: {e}", exc_info=True)

        mcp_request.status = MCPRequestStatus.FAILED
        mcp_request.error_message = str(e)
        mcp_request.completed_at = datetime.utcnow()
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/health")
async def mcp_health_check():
    """
    Check health of MCP proxy and all clients.

    Returns:
        Health status for each MCP client
    """
    try:
        proxy = await get_mcp_proxy()
        health = await proxy.health_check()
        return health

    except Exception as e:
        logger.error(f"Error checking MCP health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


@router.get("/requests/history", response_model=List[MCPToolExecuteResponse])
async def get_mcp_request_history(
    limit: int = 50,
    server_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get MCP request history for the current user.

    Args:
        limit: Maximum number of requests to return
        server_type: Optional filter by server type

    Returns:
        List of historical MCP requests
    """
    from sqlalchemy import select, desc

    # Build query
    query = (
        select(MCPRequest)
        .where(MCPRequest.user_id == current_user.id)
        .order_by(desc(MCPRequest.requested_at))
        .limit(limit)
    )

    if server_type:
        server_type_enum = {
            "github": MCPServerType.GITHUB,
            "figma": MCPServerType.FIGMA,
            "slack": MCPServerType.SLACK,
        }.get(server_type.lower())

        if server_type_enum:
            query = query.where(MCPRequest.server_type == server_type_enum)

    result = await db.execute(query)
    requests = result.scalars().all()

    # Convert to response models
    return [
        MCPToolExecuteResponse(
            request_id=req.id,
            server_type=req.server_type.value,
            tool_name=req.tool_name,
            status=req.status.value,
            result=req.response,
            error=req.error_message,
            duration_ms=req.duration_ms,
            timestamp=req.requested_at,
        )
        for req in requests
    ]
