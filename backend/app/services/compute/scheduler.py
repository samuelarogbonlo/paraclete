"""
Background scheduler for VM auto-shutdown and maintenance tasks.
"""

import asyncio
import logging
from datetime import datetime

from app.db.database import AsyncSessionLocal
from app.services.compute.vm_manager import VMManager

logger = logging.getLogger(__name__)


class VMScheduler:
    """
    Background scheduler for VM maintenance tasks.

    Runs periodic checks for:
    - Idle VM auto-shutdown
    - Cost calculation updates
    - Health monitoring
    """

    def __init__(self, check_interval: int = 60):
        """
        Initialize VM scheduler.

        Args:
            check_interval: Interval between checks in seconds (default: 60s)
        """
        self.check_interval = check_interval
        self._running = False
        self._task: asyncio.Task = None

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            logger.warning("VM scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"VM scheduler started (check interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("VM scheduler stopped")

    async def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_idle_vms()
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in VM scheduler: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _check_idle_vms(self) -> None:
        """Check for idle VMs and shut them down."""
        try:
            async with AsyncSessionLocal() as db:
                vm_manager = VMManager(db)
                shutdown_vms = await vm_manager.check_idle_vms()

                if shutdown_vms:
                    logger.info(
                        f"Auto-shutdown completed for {len(shutdown_vms)} idle VMs"
                    )

        except Exception as e:
            logger.error(f"Error checking idle VMs: {e}", exc_info=True)


# Global scheduler instance
_scheduler_instance: VMScheduler = None


def get_vm_scheduler() -> VMScheduler:
    """Get the global VM scheduler instance."""
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = VMScheduler(check_interval=60)  # Check every minute

    return _scheduler_instance


async def start_vm_scheduler() -> None:
    """Start the global VM scheduler."""
    scheduler = get_vm_scheduler()
    await scheduler.start()


async def stop_vm_scheduler() -> None:
    """Stop the global VM scheduler."""
    scheduler = get_vm_scheduler()
    await scheduler.stop()
