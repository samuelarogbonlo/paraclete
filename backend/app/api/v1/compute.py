"""
Compute API endpoints for VM management.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import User
from app.core.auth import get_current_user
from app.services.compute.vm_manager import VMManager
from app.services.compute.fly_machines import FlyMachinesError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compute", tags=["compute"])


# Request/Response Models


class VMProvisionRequest(BaseModel):
    """Request model for VM provisioning."""

    session_id: Optional[UUID] = Field(None, description="Optional session to link VM to")
    cpu_type: Optional[str] = Field(None, description="CPU type (e.g., shared-cpu-1x)")
    memory_mb: Optional[int] = Field(None, description="Memory in MB")
    region: Optional[str] = Field(None, description="Fly.io region (e.g., iad, lax)")


class VMResponse(BaseModel):
    """Response model for VM details."""

    id: str
    machine_id: str
    status: str
    cpu_type: str
    memory_mb: int
    region: Optional[str]
    provisioned_at: Optional[str]
    started_at: Optional[str]
    last_activity: Optional[str]
    auto_shutdown_at: Optional[str]
    ssh_hostname: Optional[str] = None
    tailscale_ip: Optional[str] = None


class SSHCredentials(BaseModel):
    """SSH connection credentials."""

    hostname: str
    port: str
    username: str
    machine_id: str
    region: str
    tailscale_ip: Optional[str] = None


class ComputeCostResponse(BaseModel):
    """Compute cost summary."""

    user_id: str
    period_days: int
    total_cost_cents: int
    total_cost_dollars: float
    usage_count: int


# API Endpoints


@router.post("/machines", response_model=VMResponse)
async def provision_vm(
    request: VMProvisionRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Provision a new VM for the current user.

    Args:
        request: VM provisioning request

    Returns:
        Provisioned VM details
    """
    try:
        vm_manager = VMManager(db)

        vm = await vm_manager.provision_vm(
            user_id=current_user.id,
            session_id=request.session_id,
            cpu_type=request.cpu_type,
            memory_mb=request.memory_mb,
            region=request.region,
        )

        return VMResponse(
            id=str(vm.id),
            machine_id=vm.machine_id,
            status=vm.status.value,
            cpu_type=vm.cpu_type,
            memory_mb=vm.memory_mb,
            region=vm.region,
            provisioned_at=vm.provisioned_at.isoformat() if vm.provisioned_at else None,
            started_at=vm.started_at.isoformat() if vm.started_at else None,
            last_activity=vm.last_activity.isoformat() if vm.last_activity else None,
            auto_shutdown_at=(
                vm.auto_shutdown_at.isoformat() if vm.auto_shutdown_at else None
            ),
            ssh_hostname=vm.ssh_hostname,
            tailscale_ip=vm.tailscale_ip,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FlyMachinesError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to provision VM: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error provisioning VM: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/machines", response_model=List[VMResponse])
async def list_user_vms(
    include_terminated: bool = False,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all VMs for the current user.

    Args:
        include_terminated: Include terminated VMs in results

    Returns:
        List of user's VMs
    """
    try:
        vm_manager = VMManager(db)
        vms = await vm_manager.get_user_vms(
            user_id=current_user.id,
            include_terminated=include_terminated,
        )

        return [
            VMResponse(
                id=str(vm.id),
                machine_id=vm.machine_id,
                status=vm.status.value,
                cpu_type=vm.cpu_type,
                memory_mb=vm.memory_mb,
                region=vm.region,
                provisioned_at=vm.provisioned_at.isoformat()
                if vm.provisioned_at
                else None,
                started_at=vm.started_at.isoformat() if vm.started_at else None,
                last_activity=vm.last_activity.isoformat()
                if vm.last_activity
                else None,
                auto_shutdown_at=(
                    vm.auto_shutdown_at.isoformat() if vm.auto_shutdown_at else None
                ),
                ssh_hostname=vm.ssh_hostname,
                tailscale_ip=vm.tailscale_ip,
            )
            for vm in vms
        ]

    except Exception as e:
        logger.error(f"Error listing VMs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list VMs",
        )


@router.get("/machines/{vm_id}", response_model=VMResponse)
async def get_vm_details(
    vm_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed status of a specific VM.

    Args:
        vm_id: VM ID

    Returns:
        VM details including live status from Fly.io
    """
    try:
        vm_manager = VMManager(db)
        vm_status = await vm_manager.get_vm_status(vm_id)

        if not vm_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="VM not found",
            )

        # Verify ownership
        from sqlalchemy import select
        from app.db.models import UserVM

        result = await db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm or vm.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return VMResponse(**vm_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting VM details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get VM details",
        )


@router.delete("/machines/{vm_id}")
async def terminate_vm(
    vm_id: UUID,
    force: bool = False,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Terminate a VM.

    Args:
        vm_id: VM ID
        force: Force termination even if machine is running

    Returns:
        Success confirmation
    """
    try:
        # Verify ownership
        from sqlalchemy import select
        from app.db.models import UserVM

        result = await db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="VM not found",
            )

        if vm.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        vm_manager = VMManager(db)
        success = await vm_manager.terminate_vm(vm_id, force=force)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to terminate VM",
            )

        return {"success": True, "message": "VM terminated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating VM: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/machines/{vm_id}/ssh", response_model=SSHCredentials)
async def get_vm_ssh_credentials(
    vm_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get SSH connection credentials for a VM.

    Args:
        vm_id: VM ID

    Returns:
        SSH connection details
    """
    try:
        # Verify ownership
        from sqlalchemy import select
        from app.db.models import UserVM

        result = await db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="VM not found",
            )

        if vm.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        vm_manager = VMManager(db)
        creds = await vm_manager.get_ssh_credentials(vm_id)

        if not creds:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSH credentials not available",
            )

        return SSHCredentials(**creds)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SSH credentials: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get SSH credentials",
        )


@router.post("/machines/{vm_id}/activity")
async def update_vm_activity(
    vm_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update VM activity timestamp to extend auto-shutdown.

    Args:
        vm_id: VM ID

    Returns:
        Success confirmation
    """
    try:
        # Verify ownership
        from sqlalchemy import select
        from app.db.models import UserVM

        result = await db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="VM not found",
            )

        if vm.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        vm_manager = VMManager(db)
        await vm_manager.update_vm_activity(vm_id)

        return {"success": True, "message": "Activity updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating VM activity: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update activity",
        )


@router.get("/costs", response_model=ComputeCostResponse)
async def get_compute_costs(
    days: int = 30,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get compute costs for the current user.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        Cost summary
    """
    try:
        vm_manager = VMManager(db)
        costs = await vm_manager.get_user_compute_costs(
            user_id=current_user.id,
            days=days,
        )

        return ComputeCostResponse(**costs)

    except Exception as e:
        logger.error(f"Error getting compute costs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get compute costs",
        )
