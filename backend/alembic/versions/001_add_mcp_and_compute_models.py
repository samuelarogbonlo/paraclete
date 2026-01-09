"""Add MCP and Compute models

Revision ID: 001
Revises:
Create Date: 2026-01-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create VMStatus enum
    vm_status_enum = postgresql.ENUM(
        'provisioning', 'running', 'stopped', 'terminated', 'error',
        name='vmstatus',
        create_type=False
    )
    vm_status_enum.create(op.get_bind(), checkfirst=True)

    # Create MCPServerType enum
    mcp_server_type_enum = postgresql.ENUM(
        'github', 'figma', 'slack', 'notion', 'atlassian', 'custom',
        name='mcpservertype',
        create_type=False
    )
    mcp_server_type_enum.create(op.get_bind(), checkfirst=True)

    # Create MCPRequestStatus enum
    mcp_request_status_enum = postgresql.ENUM(
        'pending', 'success', 'failed', 'timeout',
        name='mcprequeststatus',
        create_type=False
    )
    mcp_request_status_enum.create(op.get_bind(), checkfirst=True)

    # Create user_vms table
    op.create_table(
        'user_vms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), nullable=True),
        sa.Column('machine_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('machine_name', sa.String(255), nullable=True),
        sa.Column('region', sa.String(50), nullable=True),
        sa.Column('machine_config', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('status', vm_status_enum, nullable=False, server_default='provisioning', index=True),
        sa.Column('status_message', sa.Text, nullable=True),
        sa.Column('ipv4_address', sa.String(45), nullable=True),
        sa.Column('ipv6_address', sa.String(45), nullable=True),
        sa.Column('tailscale_ip', sa.String(45), nullable=True),
        sa.Column('ssh_hostname', sa.String(255), nullable=True),
        sa.Column('ssh_port', sa.Integer, nullable=False, server_default='22'),
        sa.Column('cpu_type', sa.String(50), nullable=True),
        sa.Column('memory_mb', sa.Integer, nullable=True),
        sa.Column('disk_gb', sa.Integer, nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('auto_shutdown_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provisioned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create mcp_requests table
    op.create_table(
        'mcp_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), nullable=True),
        sa.Column('server_type', mcp_server_type_enum, nullable=False, index=True),
        sa.Column('tool_name', sa.String(255), nullable=False, index=True),
        sa.Column('arguments', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('status', mcp_request_status_enum, nullable=False, server_default='pending', index=True),
        sa.Column('response', postgresql.JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('retries', sa.Integer, nullable=False, server_default='0'),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create compute_usage table
    op.create_table(
        'compute_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('vm_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_vms.id'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('cpu_type', sa.String(50), nullable=False),
        sa.Column('memory_mb', sa.Integer, nullable=False),
        sa.Column('region', sa.String(50), nullable=True),
        sa.Column('cost_per_hour', sa.Integer, nullable=False),
        sa.Column('total_cost_cents', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create indexes for better performance
    op.create_index('ix_user_vms_user_id', 'user_vms', ['user_id'])
    op.create_index('ix_mcp_requests_user_id', 'mcp_requests', ['user_id'])
    op.create_index('ix_compute_usage_user_id', 'compute_usage', ['user_id'])
    op.create_index('ix_compute_usage_vm_id', 'compute_usage', ['vm_id'])


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index('ix_compute_usage_vm_id', table_name='compute_usage')
    op.drop_index('ix_compute_usage_user_id', table_name='compute_usage')
    op.drop_index('ix_mcp_requests_user_id', table_name='mcp_requests')
    op.drop_index('ix_user_vms_user_id', table_name='user_vms')

    # Drop tables
    op.drop_table('compute_usage')
    op.drop_table('mcp_requests')
    op.drop_table('user_vms')

    # Drop enums
    sa.Enum(name='vmstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mcpservertype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mcprequeststatus').drop(op.get_bind(), checkfirst=True)
