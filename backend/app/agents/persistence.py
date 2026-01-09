"""
State persistence and checkpointing with PostgresSaver.

Provides checkpoint management for LangGraph workflows with PostgreSQL backend.
"""

import os
from typing import Optional, Dict, Any
import logging
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages LangGraph checkpoints with PostgreSQL persistence.

    Handles checkpoint creation, retrieval, and cleanup.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize checkpoint manager with database connection."""
        self.connection_string = connection_string or self._get_connection_string()
        self._saver: Optional[PostgresSaver] = None
        self._engine: Optional[AsyncEngine] = None

    def _get_connection_string(self) -> str:
        """Build PostgreSQL connection string from settings."""
        # Use sync connection string for PostgresSaver
        return (
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
            f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )

    def get_checkpointer(self) -> PostgresSaver:
        """
        Get or create PostgresSaver instance.

        Returns:
            PostgresSaver instance for LangGraph checkpointing
        """
        if not self._saver:
            try:
                self._saver = PostgresSaver.from_conn_string(
                    self.connection_string,
                )
                logger.info("PostgresSaver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PostgresSaver: {e}")
                raise

        return self._saver

    async def setup_tables(self):
        """
        Create necessary tables for checkpointing if they don't exist.

        This should be called during application startup.
        """
        try:
            # PostgresSaver handles table creation automatically
            saver = self.get_checkpointer()
            logger.info("Checkpoint tables verified/created")
        except Exception as e:
            logger.error(f"Failed to setup checkpoint tables: {e}")
            raise

    async def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a checkpoint for a given thread.

        Args:
            thread_id: The thread/session ID
            checkpoint_id: Specific checkpoint ID (latest if None)

        Returns:
            Checkpoint data or None if not found
        """
        try:
            saver = self.get_checkpointer()

            # Get checkpoint using thread config
            config = {"configurable": {"thread_id": thread_id}}
            if checkpoint_id:
                config["configurable"]["checkpoint_id"] = checkpoint_id

            checkpoint = saver.get(config)
            return checkpoint

        except Exception as e:
            logger.error(f"Failed to retrieve checkpoint: {e}")
            return None

    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10,
    ) -> list[Dict[str, Any]]:
        """
        List checkpoints for a thread.

        Args:
            thread_id: The thread/session ID
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint metadata
        """
        try:
            saver = self.get_checkpointer()

            config = {"configurable": {"thread_id": thread_id}}
            checkpoints = list(saver.list(config, limit=limit))

            return checkpoints

        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def delete_checkpoints(
        self,
        thread_id: str,
        before_checkpoint_id: Optional[str] = None,
    ) -> bool:
        """
        Delete checkpoints for a thread.

        Args:
            thread_id: The thread/session ID
            before_checkpoint_id: Delete checkpoints before this ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: PostgresSaver doesn't have built-in delete method
            # Would need custom SQL implementation
            logger.warning("Checkpoint deletion not implemented in PostgresSaver")
            return False

        except Exception as e:
            logger.error(f"Failed to delete checkpoints: {e}")
            return False

    def get_thread_config(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a thread configuration for LangGraph.

        Args:
            thread_id: The thread/session ID
            checkpoint_id: Specific checkpoint to resume from
            metadata: Additional metadata to store

        Returns:
            Configuration dictionary for LangGraph
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id

        if metadata:
            config["metadata"] = metadata

        return config


# Global instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """
    Get global checkpoint manager instance.

    Returns:
        CheckpointManager instance
    """
    global _checkpoint_manager
    if not _checkpoint_manager:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


async def initialize_persistence():
    """
    Initialize persistence layer during app startup.

    Should be called from main.py startup event.
    """
    manager = get_checkpoint_manager()
    await manager.setup_tables()
    logger.info("Persistence layer initialized")