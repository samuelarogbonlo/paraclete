"""
Fly.io Machines API client for VM management.

Wraps the Fly.io Machines API using httpx for async operations.
"""

from typing import Any, Dict, List, Optional
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FlyMachinesError(Exception):
    """Base exception for Fly.io Machines errors."""

    pass


class FlyMachinesClient:
    """
    Client for Fly.io Machines API.

    Provides methods for creating, managing, and destroying VMs.
    Rate limit: 1 request/second per action per machine (from PROJECT_PLAN.md)
    """

    def __init__(self, api_token: str, app_name: str):
        """
        Initialize Fly.io Machines client.

        Args:
            api_token: Fly.io API token
            app_name: Fly.io app name for VMs
        """
        self.api_token = api_token
        self.app_name = app_name
        self.base_url = "https://api.machines.dev/v1"

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()

    async def create_machine(
        self,
        user_id: str,
        config: Optional[Dict[str, Any]] = None,
        region: str = "iad",
    ) -> Dict[str, Any]:
        """
        Create a new VM for a user.

        Args:
            user_id: User identifier for naming/tagging
            config: Machine configuration (CPU, RAM, image, etc.)
            region: Fly.io region (default: iad = US East)

        Returns:
            Machine details including machine_id and connection info

        Example response:
            {
                "id": "148e7a5e90528e",
                "name": "paraclete-vm-user123",
                "state": "created",
                "region": "iad",
                "instance_id": "...",
                "private_ip": "...",
                "config": {...}
            }
        """
        if not config:
            # Default configuration: shared-cpu-1x with 1GB RAM
            config = {
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 1,
                    "memory_mb": 1024,
                },
                "image": "flyio/paraclete-base:latest",  # Base image with tmux, git, code-server
                "env": {
                    "USER_ID": user_id,
                },
                "services": [
                    {
                        "ports": [
                            {
                                "port": 22,
                                "handlers": ["tls"],
                            }
                        ],
                        "protocol": "tcp",
                        "internal_port": 22,
                    }
                ],
            }

        payload = {
            "name": f"paraclete-vm-{user_id[:8]}",
            "region": region,
            "config": config,
        }

        try:
            response = await self._http_client.post(
                f"{self.base_url}/apps/{self.app_name}/machines",
                json=payload,
            )
            response.raise_for_status()
            machine_data = response.json()

            logger.info(
                f"Created Fly.io machine {machine_data['id']} for user {user_id}"
            )
            return machine_data

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create machine: {e.response.text}")
            raise FlyMachinesError(f"Failed to create machine: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error creating machine: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def destroy_machine(
        self, machine_id: str, force: bool = False
    ) -> Dict[str, Any]:
        """
        Terminate a VM.

        Args:
            machine_id: Fly.io machine ID
            force: Force destroy even if machine is running

        Returns:
            Destruction confirmation

        Example response:
            {
                "ok": true
            }
        """
        try:
            params = {"force": "true"} if force else {}

            response = await self._http_client.delete(
                f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}",
                params=params,
            )
            response.raise_for_status()

            logger.info(f"Destroyed Fly.io machine {machine_id}")
            return {"ok": True}

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to destroy machine {machine_id}: {e.response.text}")
            raise FlyMachinesError(f"Failed to destroy machine: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error destroying machine: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def get_machine_status(self, machine_id: str) -> Dict[str, Any]:
        """
        Get current status of a VM.

        Args:
            machine_id: Fly.io machine ID

        Returns:
            Machine status and details

        Example response:
            {
                "id": "148e7a5e90528e",
                "name": "paraclete-vm-user123",
                "state": "started",
                "region": "iad",
                "instance_id": "...",
                "private_ip": "...",
                "created_at": "2026-01-07T12:00:00Z",
                "updated_at": "2026-01-07T12:05:00Z"
            }
        """
        try:
            response = await self._http_client.get(
                f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FlyMachinesError(f"Machine {machine_id} not found")
            logger.error(f"Failed to get machine status: {e.response.text}")
            raise FlyMachinesError(f"Failed to get status: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error getting machine status: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def start_machine(self, machine_id: str) -> Dict[str, Any]:
        """
        Start a stopped VM.

        Args:
            machine_id: Fly.io machine ID

        Returns:
            Machine status after start
        """
        try:
            response = await self._http_client.post(
                f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}/start"
            )
            response.raise_for_status()

            logger.info(f"Started Fly.io machine {machine_id}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to start machine {machine_id}: {e.response.text}")
            raise FlyMachinesError(f"Failed to start machine: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error starting machine: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def stop_machine(self, machine_id: str) -> Dict[str, Any]:
        """
        Stop a running VM.

        Args:
            machine_id: Fly.io machine ID

        Returns:
            Machine status after stop
        """
        try:
            response = await self._http_client.post(
                f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}/stop"
            )
            response.raise_for_status()

            logger.info(f"Stopped Fly.io machine {machine_id}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to stop machine {machine_id}: {e.response.text}")
            raise FlyMachinesError(f"Failed to stop machine: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error stopping machine: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def get_ssh_credentials(self, machine_id: str) -> Dict[str, str]:
        """
        Get SSH connection information for a VM.

        Args:
            machine_id: Fly.io machine ID

        Returns:
            SSH connection details

        Example response:
            {
                "hostname": "paraclete-vm-user123.fly.dev",
                "port": "22",
                "username": "root",
                "machine_id": "148e7a5e90528e"
            }
        """
        try:
            # Get machine details
            machine = await self.get_machine_status(machine_id)

            # Construct SSH info from machine details
            hostname = f"{machine['name']}.internal"  # Internal Fly.io hostname
            if "private_ip" in machine:
                hostname = machine["private_ip"]

            return {
                "hostname": hostname,
                "port": "22",
                "username": "root",
                "machine_id": machine_id,
                "region": machine.get("region", "unknown"),
            }

        except Exception as e:
            logger.error(f"Failed to get SSH credentials: {e}")
            raise FlyMachinesError(f"Failed to get SSH credentials: {e}")

    async def list_machines(
        self, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all machines in the app.

        Args:
            include_deleted: Include deleted machines in results

        Returns:
            List of machines
        """
        try:
            params = {"include_deleted": "true"} if include_deleted else {}

            response = await self._http_client.get(
                f"{self.base_url}/apps/{self.app_name}/machines",
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list machines: {e.response.text}")
            raise FlyMachinesError(f"Failed to list machines: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error listing machines: {e}")
            raise FlyMachinesError(f"Unexpected error: {e}")

    async def update_machine_metadata(
        self, machine_id: str, metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Update machine metadata/labels.

        Args:
            machine_id: Fly.io machine ID
            metadata: Metadata key-value pairs

        Returns:
            Updated machine details
        """
        try:
            # Get current machine config
            machine = await self.get_machine_status(machine_id)

            # Update config with new metadata
            config = machine.get("config", {})
            if "metadata" not in config:
                config["metadata"] = {}
            config["metadata"].update(metadata)

            # Update machine
            response = await self._http_client.post(
                f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}",
                json={"config": config},
            )
            response.raise_for_status()

            logger.info(f"Updated metadata for machine {machine_id}")
            return response.json()

        except Exception as e:
            logger.error(f"Failed to update machine metadata: {e}")
            raise FlyMachinesError(f"Failed to update metadata: {e}")
