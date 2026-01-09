# MCP Proxy Server and Cloud Compute Infrastructure

## Overview

This document describes the MCP (Model Context Protocol) proxy server and cloud compute infrastructure for Paraclete backend. This is Phase 3 infrastructure that enables AI agents to execute tools via MCP and provision cloud VMs for users.

## Architecture

```
┌─────────────────┐
│  Mobile Client  │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌────────────────────────────────┐    │
│  │      MCP Proxy Server          │    │
│  │  ┌──────────────────────────┐  │    │
│  │  │  GitHubMCPClient         │  │    │
│  │  │  FigmaMCPClient          │  │    │
│  │  │  SlackMCPClient          │  │    │
│  │  └──────────────────────────┘  │    │
│  └────────────────────────────────┘    │
│  ┌────────────────────────────────┐    │
│  │   Compute Service              │    │
│  │  ┌──────────────────────────┐  │    │
│  │  │  FlyMachinesClient       │  │    │
│  │  │  VMManager               │  │    │
│  │  │  VMScheduler             │  │    │
│  │  └──────────────────────────┘  │    │
│  └────────────────────────────────┘    │
└──────────────┬──────────────┬──────────┘
               │              │
               ▼              ▼
       ┌──────────────┐ ┌─────────────┐
       │ MCP Servers  │ │  Fly.io VMs │
       │ (GitHub,etc) │ │ + Tailscale │
       └──────────────┘ └─────────────┘
```

## MCP Proxy Server

### Components

#### 1. MCPProxyServer (`app/mcp/proxy.py`)

Central routing server that:
- Manages connections to multiple MCP servers
- Routes tool invocations to appropriate clients
- Handles authentication token passthrough
- Implements retry logic with exponential backoff
- Provides health monitoring

**Key Methods:**
- `list_servers()` - List all available MCP servers
- `list_tools(server_type, auth_token)` - Get tools from specific server
- `execute_tool(server_type, tool_name, arguments, auth_token)` - Execute MCP tool
- `health_check()` - Check health of all clients

#### 2. MCP Clients (`app/mcp/clients/`)

**GitHubMCPClient** - Connects to official GitHub MCP server
- Repository operations (create, clone, search)
- Issue management
- Pull request operations
- Code search
- File operations

**FigmaMCPClient** - Integrates with Figma MCP server
- Design file access
- Component extraction
- Collaboration features

**SlackMCPClient** - Slack integration
- Send messages
- Channel management
- Team notifications

### API Endpoints

All endpoints require authentication via JWT token.

#### GET `/v1/mcp/servers`

List all available MCP servers.

**Response:**
```json
[
  {
    "server_type": "github",
    "status": "available",
    "tools_count": 6,
    "requires_auth": true
  }
]
```

#### GET `/v1/mcp/{server_type}/tools`

List tools available from a specific MCP server.

**Headers:**
- `X-Auth-Token`: Service-specific auth token (e.g., GitHub token)

**Response:**
```json
[
  {
    "name": "create_repository",
    "description": "Create a new GitHub repository",
    "inputSchema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "private": {"type": "boolean"}
      },
      "required": ["name"]
    }
  }
]
```

#### POST `/v1/mcp/{server_type}/execute`

Execute an MCP tool.

**Headers:**
- `X-Auth-Token`: Service-specific auth token

**Request Body:**
```json
{
  "tool_name": "create_repository",
  "arguments": {
    "name": "my-new-repo",
    "private": false
  },
  "session_id": "uuid-optional"
}
```

**Response:**
```json
{
  "request_id": "uuid",
  "server_type": "github",
  "tool_name": "create_repository",
  "status": "success",
  "result": {
    "id": 123456,
    "name": "my-new-repo",
    "html_url": "https://github.com/user/my-new-repo"
  },
  "duration_ms": 450,
  "timestamp": "2026-01-07T12:00:00Z"
}
```

#### GET `/v1/mcp/requests/history`

Get MCP request history for the current user.

**Query Parameters:**
- `limit` (default: 50) - Max results
- `server_type` - Filter by server type

## Compute Service

### Components

#### 1. FlyMachinesClient (`app/services/compute/fly_machines.py`)

Wraps Fly.io Machines API for VM management.

**Key Methods:**
- `create_machine(user_id, config, region)` - Provision new VM
- `destroy_machine(machine_id, force)` - Terminate VM
- `get_machine_status(machine_id)` - Get VM status
- `start_machine(machine_id)` - Start stopped VM
- `stop_machine(machine_id)` - Stop running VM
- `get_ssh_credentials(machine_id)` - Get SSH connection info

#### 2. VMManager (`app/services/compute/vm_manager.py`)

High-level VM lifecycle management with:
- User VM provisioning with isolation
- Automatic shutdown after idle timeout
- Cost tracking per user
- Resource limit enforcement

**Key Methods:**
- `provision_vm(user_id, session_id, cpu_type, memory_mb, region)` - Create VM
- `terminate_vm(vm_id, force)` - Destroy VM
- `get_vm_status(vm_id)` - Get VM details
- `update_vm_activity(vm_id)` - Update activity timestamp
- `check_idle_vms()` - Auto-shutdown idle VMs
- `get_user_compute_costs(user_id, days)` - Calculate costs

#### 3. VMScheduler (`app/services/compute/scheduler.py`)

Background task that runs every 60 seconds to:
- Check for idle VMs (last activity > 30 minutes)
- Automatically terminate idle VMs
- Clean up resources

### Database Models

#### UserVM
Tracks user VM allocations:
- Machine ID, name, region
- Status (provisioning, running, stopped, terminated, error)
- Resource details (CPU type, memory, disk)
- Network info (IPs, SSH hostname, Tailscale IP)
- Activity tracking (last activity, auto-shutdown time)
- Timestamps (provisioned, started, stopped, terminated)

#### MCPRequest
Logs MCP operations for debugging:
- Server type, tool name, arguments
- Status (pending, success, failed, timeout)
- Response data or error message
- Performance metrics (duration, retries)

#### ComputeUsage
Tracks compute usage for cost tracking:
- Start/end time, duration
- Resource details (CPU type, memory, region)
- Cost calculation (per-hour rate, total cost)

### API Endpoints

#### POST `/v1/compute/machines`

Provision a new VM for the current user.

**Request Body:**
```json
{
  "session_id": "uuid-optional",
  "cpu_type": "shared-cpu-1x",
  "memory_mb": 1024,
  "region": "iad"
}
```

**Response:**
```json
{
  "id": "vm-uuid",
  "machine_id": "fly-machine-id",
  "status": "provisioning",
  "cpu_type": "shared-cpu-1x",
  "memory_mb": 1024,
  "region": "iad",
  "provisioned_at": "2026-01-07T12:00:00Z",
  "auto_shutdown_at": "2026-01-07T12:30:00Z"
}
```

#### GET `/v1/compute/machines`

List all VMs for the current user.

**Query Parameters:**
- `include_terminated` (default: false)

#### GET `/v1/compute/machines/{vm_id}`

Get detailed status of a specific VM.

#### DELETE `/v1/compute/machines/{vm_id}`

Terminate a VM.

**Query Parameters:**
- `force` (default: false) - Force termination

#### GET `/v1/compute/machines/{vm_id}/ssh`

Get SSH credentials for connecting to a VM.

**Response:**
```json
{
  "hostname": "fdaa:0:1:a7b:1::1",
  "port": "22",
  "username": "root",
  "machine_id": "fly-machine-id",
  "region": "iad",
  "tailscale_ip": "100.64.0.1"
}
```

#### POST `/v1/compute/machines/{vm_id}/activity`

Update VM activity to extend auto-shutdown timer.

#### GET `/v1/compute/costs`

Get compute costs for the current user.

**Query Parameters:**
- `days` (default: 30)

**Response:**
```json
{
  "user_id": "uuid",
  "period_days": 30,
  "total_cost_cents": 500,
  "total_cost_dollars": 5.00,
  "usage_count": 10
}
```

## Configuration

Add these to `.env`:

```bash
# Fly.io Configuration
FLY_API_TOKEN=your-fly-api-token
FLY_APP_NAME=paraclete-vms
FLY_ORG_SLUG=your-org-slug

# VM Configuration
VM_DEFAULT_REGION=iad
VM_DEFAULT_CPU_TYPE=shared-cpu-1x
VM_DEFAULT_MEMORY_MB=1024
VM_IDLE_TIMEOUT_MINUTES=30
VM_MAX_PER_USER=3

# Tailscale
TAILSCALE_AUTH_KEY=your-tailscale-key

# MCP Server URLs (optional for remote servers)
MCP_GITHUB_SERVER_URL=http://github-mcp-server
MCP_FIGMA_SERVER_URL=http://figma-mcp-server
MCP_SLACK_SERVER_URL=http://slack-mcp-server
MCP_REQUEST_TIMEOUT_SECONDS=30
MCP_MAX_RETRIES=3
```

## Pricing and Cost Tracking

### Fly.io Pricing (from PROJECT_PLAN.md)

| Plan | CPU | RAM | Cost/Hour (cents) |
|------|-----|-----|-------------------|
| shared-cpu-1x | 1 shared | 256MB | 0.27 |
| shared-cpu-1x | 1 shared | 1GB | 0.79 |
| performance-cpu-2x | 2 dedicated | 4GB | 6.2 |

### Cost Tracking

The system tracks compute usage in the `ComputeUsage` table:
- Records start/end time for each VM session
- Calculates duration in seconds
- Stores cost per hour in cents
- Computes total cost on VM termination

Users can query their costs via the `/v1/compute/costs` endpoint.

## Auto-Shutdown Mechanism

VMs automatically shut down after 30 minutes of inactivity (configurable via `VM_IDLE_TIMEOUT_MINUTES`).

**How it works:**
1. VM provisioned with `auto_shutdown_at` timestamp
2. Mobile app calls `/v1/compute/machines/{vm_id}/activity` on user interaction
3. Each activity call extends `auto_shutdown_at` by 30 minutes
4. VMScheduler runs every 60 seconds
5. Scheduler terminates VMs where `auto_shutdown_at` has passed

**Note:** Users receive a warning before shutdown if they have push notifications enabled.

## Tailscale Integration

Each VM is automatically configured with Tailscale for secure networking.

**Setup Script:** `/backend/scripts/setup_tailscale.sh`

This script:
- Installs Tailscale on the VM
- Authenticates with provided auth key
- Enables SSH over Tailscale
- Stores Tailscale IP for connection

**User Isolation:**
- Each user gets dedicated VMs
- VMs are tagged with user ID
- Network isolation via Tailscale
- No cross-user access

## Testing

Run tests with:

```bash
# All tests
pytest

# MCP tests only
pytest tests/test_mcp/

# Compute tests only
pytest tests/test_compute/

# Specific test file
pytest tests/test_mcp/test_github_client.py -v
```

## Database Migration

Apply the migration:

```bash
# Run migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Integration with LangGraph Agents

The MCP proxy and compute service integrate with LangGraph agents (Wave 2):

1. **MCP Tool Execution:**
   - LangGraph agents call `/v1/mcp/{server}/execute` to use GitHub, Figma, Slack
   - Agents receive tool schemas via `/v1/mcp/{server}/tools`
   - Authentication tokens passed from user's encrypted keys

2. **VM Access:**
   - Terminal feature provisions VM via `/v1/compute/machines`
   - Mobile app receives SSH credentials
   - User connects via dartssh2 + xterm.dart
   - Activity updates prevent auto-shutdown during active session

3. **Cost Tracking:**
   - All VM usage tracked per user
   - Agents can query costs before expensive operations
   - Cost warnings shown to users

## Security Considerations

1. **Authentication:**
   - All endpoints require valid JWT
   - Service tokens (GitHub, Figma) never logged or stored
   - Tokens passed via `X-Auth-Token` header

2. **VM Isolation:**
   - Each user gets dedicated VMs
   - Tailscale provides encrypted tunnel
   - SSH keys managed per user

3. **Rate Limiting:**
   - Fly.io: 1 request/second per action per machine
   - Implement rate limiting on API endpoints (TODO)

4. **Resource Limits:**
   - Max 3 concurrent VMs per user (configurable)
   - Auto-shutdown prevents runaway costs
   - Cost tracking alerts on high usage

## Troubleshooting

### MCP Connection Issues

Check MCP proxy health:
```bash
curl http://localhost:8000/v1/mcp/health
```

View MCP request logs:
```sql
SELECT * FROM mcp_requests
WHERE user_id = 'uuid'
ORDER BY requested_at DESC
LIMIT 10;
```

### VM Provisioning Failures

Check Fly.io status:
```bash
fly status -a paraclete-vms
```

View VM logs:
```sql
SELECT * FROM user_vms
WHERE status = 'error'
ORDER BY created_at DESC;
```

### Auto-Shutdown Not Working

Check scheduler is running:
- Look for "VM scheduler started" in app logs
- Verify `FLY_API_TOKEN` is set

Manually trigger check:
```python
from app.services.compute.vm_manager import VMManager
from app.db.database import async_session_maker

async with async_session_maker() as db:
    manager = VMManager(db)
    shutdown_vms = await manager.check_idle_vms()
    print(f"Shut down {len(shutdown_vms)} VMs")
```

## Future Enhancements

1. **Pre-warmed VM Pool:** Maintain pool of ready VMs for instant provisioning
2. **GPU Support:** Add GPU machine types for AI workloads
3. **Custom Images:** Allow users to build custom VM images
4. **Multi-Region:** Automatic region selection based on user location
5. **Cost Alerts:** Push notifications when costs exceed threshold
6. **Snapshot/Backup:** VM state snapshots for session continuity

## References

- [Fly.io Machines API](https://fly.io/docs/machines/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Tailscale Documentation](https://tailscale.com/kb/)
