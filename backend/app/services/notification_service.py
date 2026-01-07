"""
Push notification service using Firebase Cloud Messaging.
"""
from typing import List, Dict, Any, Optional
import logging

from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications to mobile clients."""

    def __init__(self):
        """Initialize notification service."""
        self.fcm_initialized = False
        self._init_firebase()

    def _init_firebase(self) -> None:
        """Initialize Firebase Admin SDK if not already initialized."""
        try:
            import firebase_admin
            from firebase_admin import messaging

            # Check if already initialized
            try:
                firebase_admin.get_app()
                self.fcm_initialized = True
                logger.info("Firebase already initialized")
            except ValueError:
                # Not initialized, will be initialized in main.py
                logger.info("Firebase will be initialized on startup")
                pass

        except ImportError:
            logger.warning("Firebase Admin SDK not available")
            self.fcm_initialized = False

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
    ) -> bool:
        """
        Send a push notification to a single device.

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional data payload
            priority: Notification priority (high/normal)

        Returns:
            True if successful, False otherwise

        Raises:
            ExternalServiceError: If FCM fails
        """
        if not self.fcm_initialized:
            logger.warning("FCM not initialized, skipping notification")
            return False

        try:
            from firebase_admin import messaging

            # Create message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound="default",
                        click_action="FLUTTER_NOTIFICATION_CLICK",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        )
                    )
                ),
            )

            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent notification: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise ExternalServiceError("FCM", str(e))

    async def send_batch_notifications(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send notifications to multiple devices.

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Dictionary with success count and failed tokens
        """
        if not self.fcm_initialized:
            logger.warning("FCM not initialized, skipping batch notification")
            return {"success_count": 0, "failure_count": len(tokens), "failed_tokens": tokens}

        try:
            from firebase_admin import messaging

            # Create messages
            messages = [
                messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                    token=token,
                )
                for token in tokens
            ]

            # Send batch
            response = messaging.send_all(messages)

            # Process results
            failed_tokens = []
            for idx, result in enumerate(response.responses):
                if not result.success:
                    failed_tokens.append(tokens[idx])
                    logger.warning(f"Failed to send to token {tokens[idx]}: {result.exception}")

            logger.info(
                f"Batch send complete: {response.success_count} success, "
                f"{response.failure_count} failures"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens,
            }

        except Exception as e:
            logger.error(f"Failed to send batch notifications: {e}")
            raise ExternalServiceError("FCM", str(e))

    async def send_agent_status_notification(
        self,
        token: str,
        session_id: str,
        agent_name: str,
        status: str,
        message: str,
    ) -> bool:
        """
        Send notification about agent status change.

        Args:
            token: FCM device token
            session_id: Session ID
            agent_name: Name of the agent
            status: Agent status
            message: Status message

        Returns:
            True if successful
        """
        title = f"{agent_name} Agent Update"
        body = message

        data = {
            "type": "agent_status",
            "session_id": session_id,
            "agent": agent_name,
            "status": status,
        }

        return await self.send_notification(token, title, body, data)

    async def send_approval_required_notification(
        self,
        token: str,
        session_id: str,
        action_type: str,
        description: str,
    ) -> bool:
        """
        Send notification when approval is required.

        Args:
            token: FCM device token
            session_id: Session ID
            action_type: Type of action requiring approval
            description: Description of the action

        Returns:
            True if successful
        """
        title = "Approval Required"
        body = f"{action_type}: {description}"

        data = {
            "type": "approval_required",
            "session_id": session_id,
            "action_type": action_type,
        }

        return await self.send_notification(
            token, title, body, data, priority="high"
        )

    async def send_session_complete_notification(
        self,
        token: str,
        session_id: str,
        summary: str,
    ) -> bool:
        """
        Send notification when a session completes.

        Args:
            token: FCM device token
            session_id: Session ID
            summary: Session summary

        Returns:
            True if successful
        """
        title = "Session Complete"
        body = summary

        data = {
            "type": "session_complete",
            "session_id": session_id,
        }

        return await self.send_notification(token, title, body, data)