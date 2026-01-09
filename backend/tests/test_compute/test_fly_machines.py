"""
Tests for Fly.io Machines client.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.services.compute.fly_machines import FlyMachinesClient, FlyMachinesError


@pytest.fixture
def fly_client():
    """Create Fly.io Machines client instance."""
    return FlyMachinesClient(api_token="test_token", app_name="test-app")


@pytest.mark.asyncio
async def test_client_initialization(fly_client):
    """Test client initialization."""
    assert fly_client.api_token == "test_token"
    assert fly_client.app_name == "test-app"
    assert fly_client.base_url == "https://api.machines.dev/v1"
    assert fly_client._http_client is not None


@pytest.mark.asyncio
async def test_create_machine_success(fly_client):
    """Test successful machine creation."""
    mock_response = {
        "id": "test_machine_id",
        "name": "paraclete-vm-user123",
        "state": "created",
        "region": "iad",
        "private_ip": "fdaa:0:1:a7b:1::1",
    }

    with patch.object(
        fly_client._http_client, "post", new=AsyncMock()
    ) as mock_post:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_post.return_value = mock_response_obj

        result = await fly_client.create_machine(
            user_id="user123",
            region="iad",
        )

        assert result["id"] == "test_machine_id"
        assert result["name"] == "paraclete-vm-user123"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_create_machine_failure(fly_client):
    """Test machine creation failure."""
    with patch.object(
        fly_client._http_client, "post", new=AsyncMock()
    ) as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            "Error",
            request=Mock(),
            response=Mock(status_code=500, text="Server error"),
        )

        with pytest.raises(FlyMachinesError):
            await fly_client.create_machine(user_id="user123")


@pytest.mark.asyncio
async def test_destroy_machine_success(fly_client):
    """Test successful machine destruction."""
    with patch.object(
        fly_client._http_client, "delete", new=AsyncMock()
    ) as mock_delete:
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()
        mock_delete.return_value = mock_response_obj

        result = await fly_client.destroy_machine("test_machine_id")

        assert result["ok"] is True
        mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_get_machine_status_success(fly_client):
    """Test getting machine status."""
    mock_response = {
        "id": "test_machine_id",
        "state": "started",
        "region": "iad",
    }

    with patch.object(fly_client._http_client, "get", new=AsyncMock()) as mock_get:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_get.return_value = mock_response_obj

        result = await fly_client.get_machine_status("test_machine_id")

        assert result["id"] == "test_machine_id"
        assert result["state"] == "started"


@pytest.mark.asyncio
async def test_get_machine_status_not_found(fly_client):
    """Test getting status of non-existent machine."""
    with patch.object(fly_client._http_client, "get", new=AsyncMock()) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            "Error",
            request=Mock(),
            response=Mock(status_code=404, text="Not found"),
        )

        with pytest.raises(FlyMachinesError, match="not found"):
            await fly_client.get_machine_status("nonexistent_id")


@pytest.mark.asyncio
async def test_start_machine(fly_client):
    """Test starting a machine."""
    mock_response = {"id": "test_machine_id", "state": "started"}

    with patch.object(
        fly_client._http_client, "post", new=AsyncMock()
    ) as mock_post:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_post.return_value = mock_response_obj

        result = await fly_client.start_machine("test_machine_id")

        assert result["state"] == "started"


@pytest.mark.asyncio
async def test_stop_machine(fly_client):
    """Test stopping a machine."""
    mock_response = {"id": "test_machine_id", "state": "stopped"}

    with patch.object(
        fly_client._http_client, "post", new=AsyncMock()
    ) as mock_post:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_post.return_value = mock_response_obj

        result = await fly_client.stop_machine("test_machine_id")

        assert result["state"] == "stopped"


@pytest.mark.asyncio
async def test_get_ssh_credentials(fly_client):
    """Test getting SSH credentials."""
    mock_machine = {
        "id": "test_machine_id",
        "name": "test-vm",
        "private_ip": "fdaa:0:1:a7b:1::1",
        "region": "iad",
    }

    with patch.object(fly_client, "get_machine_status") as mock_status:
        mock_status.return_value = mock_machine

        creds = await fly_client.get_ssh_credentials("test_machine_id")

        assert creds["machine_id"] == "test_machine_id"
        assert creds["username"] == "root"
        assert creds["port"] == "22"
        assert creds["region"] == "iad"


@pytest.mark.asyncio
async def test_list_machines(fly_client):
    """Test listing all machines."""
    mock_response = [
        {"id": "machine1", "name": "vm1"},
        {"id": "machine2", "name": "vm2"},
    ]

    with patch.object(fly_client._http_client, "get", new=AsyncMock()) as mock_get:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_get.return_value = mock_response_obj

        result = await fly_client.list_machines()

        assert len(result) == 2
        assert result[0]["id"] == "machine1"
