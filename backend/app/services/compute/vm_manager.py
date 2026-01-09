"""
VM Manager for high-level VM lifecycle management.

Handles VM provisioning, tracking, auto-shutdown, and cost calculation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import UserVM, VMStatus, ComputeUsage, User
from app.services.compute.fly_machines import FlyMachinesClient, FlyMachinesError
from app.config import settings

logger = logging.getLogger(__name__)


# Fly.io pricing in cents per hour (from PROJECT_PLAN.md)
FLY_PRICING = {
    "shared-cpu-1x": {
        "256": 0.27,  # 256MB RAM = $0.0027/hr = 0.27 cents
        "1024": 0.79,  # 1GB RAM = $0.0079/hr = 0.79 cents
    },
    "performance-cpu-2x": {
        "4096": 6.2,  # 4GB RAM = $0.062/hr = 6.2 cents
    },
}


class VMManager:
    """
    High-level VM manager with auto-shutdown and cost tracking.

    Features:
    - User VM provisioning with isolation
    - Automatic shutdown after idle timeout
    - Cost tracking per user
    - Resource limit enforcement
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize VM manager.

        Args:
            db: Database session
        """
        self.db = db

        # Initialize Fly.io client if token available
        if settings.FLY_API_TOKEN:
            self.fly_client = FlyMachinesClient(
                api_token=settings.FLY_API_TOKEN,
                app_name=settings.FLY_APP_NAME,
            )
        else:
            self.fly_client = None
            logger.warning("FLY_API_TOKEN not set, VM operations will fail")

    async def provision_vm(
        self,
        user_id: UUID,
        session_id: Optional[UUID] = None,
        cpu_type: Optional[str] = None,
        memory_mb: Optional[int] = None,
        region: Optional[str] = None,
    ) -> UserVM:
        """
        Provision a new VM for a user.

        Args:
            user_id: User ID
            session_id: Optional session to link VM to
            cpu_type: CPU type (default from settings)
            memory_mb: Memory in MB (default from settings)
            region: Fly.io region (default from settings)

        Returns:
            UserVM record

        Raises:
            ValueError: If user has too many VMs
            FlyMachinesError: If provisioning fails
        """
        if not self.fly_client:
            raise FlyMachinesError("Fly.io client not configured")

        # Check user VM limit
        active_vms_count = await self._count_active_vms(user_id)
        if active_vms_count >= settings.VM_MAX_PER_USER:
            raise ValueError(
                f"User has reached maximum VM limit ({settings.VM_MAX_PER_USER})"
            )

        # Use defaults if not specified
        cpu_type = cpu_type or settings.VM_DEFAULT_CPU_TYPE
        memory_mb = memory_mb or settings.VM_DEFAULT_MEMORY_MB
        region = region or settings.VM_DEFAULT_REGION

        # Calculate auto-shutdown time
        auto_shutdown_at = datetime.utcnow() + timedelta(
            minutes=settings.VM_IDLE_TIMEOUT_MINUTES
        )

        try:
            # Create VM via Fly.io
            machine_config = {
                "guest": {
                    "cpu_kind": "shared" if "shared" in cpu_type else "performance",
                    "cpus": int(cpu_type.split("-")[-1].replace("x", "")),
                    "memory_mb": memory_mb,
                },
                "image": "flyio/paraclete-base:latest",
                "env": {
                    "USER_ID": str(user_id),
                    "TAILSCALE_AUTHKEY": settings.TAILSCALE_AUTH_KEY or "",
                },
            }

            machine = await self.fly_client.create_machine(
                user_id=str(user_id),
                config=machine_config,
                region=region,
            )

            # Create database record
            vm = UserVM(
                user_id=user_id,
                session_id=session_id,
                machine_id=machine["id"],
                machine_name=machine.get("name"),
                region=machine.get("region"),
                machine_config=machine.get("config", {}),
                status=VMStatus.PROVISIONING,
                cpu_type=cpu_type,
                memory_mb=memory_mb,
                auto_shutdown_at=auto_shutdown_at,
                ipv4_address=machine.get("private_ip"),
            )

            self.db.add(vm)
            await self.db.commit()
            await self.db.refresh(vm)

            # Start tracking compute usage
            await self._start_usage_tracking(vm)

            logger.info(f"Provisioned VM {vm.machine_id} for user {user_id}")

            # Start machine if it's not already started
            try:
                await self.fly_client.start_machine(machine["id"])
                vm.status = VMStatus.RUNNING
                vm.started_at = datetime.utcnow()
                await self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to start machine {machine['id']}: {e}")

            return vm

        except Exception as e:
            logger.error(f"Failed to provision VM for user {user_id}: {e}")
            raise FlyMachinesError(f"Failed to provision VM: {e}")

    async def terminate_vm(self, vm_id: UUID, force: bool = False) -> bool:
        """
        Terminate a VM and clean up resources.

        Args:
            vm_id: VM database ID
            force: Force termination even if machine is running

        Returns:
            True if successful, False otherwise
        """
        if not self.fly_client:
            raise FlyMachinesError("Fly.io client not configured")

        # Get VM record
        result = await self.db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm:
            logger.warning(f"VM {vm_id} not found")
            return False

        try:
            # Destroy Fly.io machine
            await self.fly_client.destroy_machine(vm.machine_id, force=force)

            # End usage tracking
            await self._end_usage_tracking(vm)

            # Update VM status
            vm.status = VMStatus.TERMINATED
            vm.terminated_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Terminated VM {vm.machine_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate VM {vm.machine_id}: {e}")
            vm.status = VMStatus.ERROR
            vm.status_message = str(e)
            await self.db.commit()
            return False

    async def get_vm_status(self, vm_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get VM status from database and Fly.io.

        Args:
            vm_id: VM database ID

        Returns:
            VM status details
        """
        # Get VM record
        result = await self.db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm:
            return None

        vm_info = {
            "id": str(vm.id),
            "machine_id": vm.machine_id,
            "status": vm.status.value,
            "cpu_type": vm.cpu_type,
            "memory_mb": vm.memory_mb,
            "region": vm.region,
            "provisioned_at": vm.provisioned_at.isoformat() if vm.provisioned_at else None,
            "started_at": vm.started_at.isoformat() if vm.started_at else None,
            "last_activity": vm.last_activity.isoformat() if vm.last_activity else None,
            "auto_shutdown_at": vm.auto_shutdown_at.isoformat() if vm.auto_shutdown_at else None,
        }

        # Get live status from Fly.io if client available
        if self.fly_client and vm.status != VMStatus.TERMINATED:
            try:
                machine_status = await self.fly_client.get_machine_status(vm.machine_id)
                vm_info["machine_state"] = machine_status.get("state")
                vm_info["instance_id"] = machine_status.get("instance_id")
            except Exception as e:
                logger.warning(f"Failed to get machine status from Fly.io: {e}")

        return vm_info

    async def get_ssh_credentials(self, vm_id: UUID) -> Optional[Dict[str, str]]:
        """
        Get SSH credentials for connecting to a VM.

        Args:
            vm_id: VM database ID

        Returns:
            SSH connection details
        """
        if not self.fly_client:
            raise FlyMachinesError("Fly.io client not configured")

        # Get VM record
        result = await self.db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if not vm or vm.status == VMStatus.TERMINATED:
            return None

        try:
            creds = await self.fly_client.get_ssh_credentials(vm.machine_id)

            # Add Tailscale IP if available
            if vm.tailscale_ip:
                creds["tailscale_ip"] = vm.tailscale_ip

            return creds

        except Exception as e:
            logger.error(f"Failed to get SSH credentials for VM {vm_id}: {e}")
            return None

    async def update_vm_activity(self, vm_id: UUID) -> None:
        """
        Update last activity timestamp and extend auto-shutdown.

        Args:
            vm_id: VM database ID
        """
        result = await self.db.execute(select(UserVM).where(UserVM.id == vm_id))
        vm = result.scalar_one_or_none()

        if vm and vm.status == VMStatus.RUNNING:
            vm.last_activity = datetime.utcnow()
            vm.auto_shutdown_at = datetime.utcnow() + timedelta(
                minutes=settings.VM_IDLE_TIMEOUT_MINUTES
            )
            await self.db.commit()
            logger.debug(f"Updated activity for VM {vm_id}")

    async def check_idle_vms(self) -> List[UUID]:
        """
        Check for idle VMs and shut them down.

        Returns:
            List of VM IDs that were shut down
        """
        now = datetime.utcnow()

        # Find VMs that should be shut down
        result = await self.db.execute(
            select(UserVM).where(
                and_(
                    UserVM.status == VMStatus.RUNNING,
                    UserVM.auto_shutdown_at <= now,
                )
            )
        )
        idle_vms = result.scalars().all()

        shutdown_vm_ids = []

        for vm in idle_vms:
            logger.info(f"Auto-shutting down idle VM {vm.machine_id}")
            try:
                await self.terminate_vm(vm.id, force=True)
                shutdown_vm_ids.append(vm.id)
            except Exception as e:
                logger.error(f"Failed to auto-shutdown VM {vm.machine_id}: {e}")

        return shutdown_vm_ids

    async def get_user_vms(
        self, user_id: UUID, include_terminated: bool = False
    ) -> List[UserVM]:
        """
        Get all VMs for a user.

        Args:
            user_id: User ID
            include_terminated: Include terminated VMs

        Returns:
            List of UserVM records
        """
        query = select(UserVM).where(UserVM.user_id == user_id)

        if not include_terminated:
            query = query.where(UserVM.status != VMStatus.TERMINATED)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _count_active_vms(self, user_id: UUID) -> int:
        """Count active VMs for a user."""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(UserVM.id)).where(
                and_(
                    UserVM.user_id == user_id,
                    UserVM.status.in_([VMStatus.PROVISIONING, VMStatus.RUNNING]),
                )
            )
        )
        return result.scalar() or 0

    async def _start_usage_tracking(self, vm: UserVM) -> None:
        """Start tracking compute usage for a VM."""
        # Calculate cost per hour in cents
        cost_per_hour = FLY_PRICING.get(vm.cpu_type, {}).get(str(vm.memory_mb), 0)

        usage = ComputeUsage(
            user_id=vm.user_id,
            vm_id=vm.id,
            start_time=datetime.utcnow(),
            cpu_type=vm.cpu_type,
            memory_mb=vm.memory_mb,
            region=vm.region,
            cost_per_hour=int(cost_per_hour * 100),  # Convert to cents
        )

        self.db.add(usage)
        await self.db.commit()
        logger.debug(f"Started usage tracking for VM {vm.id}")

    async def _end_usage_tracking(self, vm: UserVM) -> None:
        """End usage tracking and calculate final cost."""
        # Find active usage records
        result = await self.db.execute(
            select(ComputeUsage).where(
                and_(
                    ComputeUsage.vm_id == vm.id,
                    ComputeUsage.end_time.is_(None),
                )
            )
        )
        usage_records = result.scalars().all()

        now = datetime.utcnow()

        for usage in usage_records:
            usage.end_time = now
            duration_seconds = int((now - usage.start_time).total_seconds())
            usage.duration_seconds = duration_seconds

            # Calculate cost: (duration_hours * cost_per_hour)
            duration_hours = duration_seconds / 3600.0
            usage.total_cost_cents = int(
                duration_hours * (usage.cost_per_hour / 100.0) * 100
            )

        await self.db.commit()
        logger.debug(f"Ended usage tracking for VM {vm.id}")

    async def get_user_compute_costs(
        self, user_id: UUID, days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate total compute costs for a user.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Cost summary
        """
        from sqlalchemy import func

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get total cost
        result = await self.db.execute(
            select(func.sum(ComputeUsage.total_cost_cents)).where(
                and_(
                    ComputeUsage.user_id == user_id,
                    ComputeUsage.start_time >= start_date,
                )
            )
        )
        total_cost_cents = result.scalar() or 0

        # Get usage count
        result = await self.db.execute(
            select(func.count(ComputeUsage.id)).where(
                and_(
                    ComputeUsage.user_id == user_id,
                    ComputeUsage.start_time >= start_date,
                )
            )
        )
        usage_count = result.scalar() or 0

        return {
            "user_id": str(user_id),
            "period_days": days,
            "total_cost_cents": total_cost_cents,
            "total_cost_dollars": total_cost_cents / 100.0,
            "usage_count": usage_count,
        }
