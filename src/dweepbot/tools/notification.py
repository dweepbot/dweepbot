"""
Notification tool for sending webhooks to Discord, Slack, etc.
"""

import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl
from .base import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NotificationInput(BaseModel):
    """Input schema for notifications."""
    message: str = Field(..., description="Message to send")
    channel: str = Field(default="default", description="Channel/webhook name")


class NotificationTool(BaseTool):
    """
    Send notifications via webhooks.
    
    Supports Discord, Slack, and generic webhooks.
    """
    
    name = "notification"
    description = "Send notifications via Discord/Slack webhooks"
    input_schema = NotificationInput
    
    def __init__(self, webhooks: Optional[Dict[str, str]] = None):
        """
        Initialize notification tool.
        
        Args:
            webhooks: Dict mapping channel names to webhook URLs
        """
        super().__init__()
        self.webhooks = webhooks or {}
    
    async def _execute(
        self,
        message: str,
        channel: str = "default",
    ) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            message: Message to send
            channel: Channel name (must be configured in webhooks)
        
        Returns:
            Dict with send status
        """
        if channel not in self.webhooks:
            raise ToolError(
                f"Channel '{channel}' not configured. "
                f"Available channels: {', '.join(self.webhooks.keys())}"
            )
        
        webhook_url = self.webhooks[channel]
        
        logger.info("Sending notification", channel=channel, message_length=len(message))
        
        try:
            # Detect webhook type and format payload
            if "discord.com" in webhook_url:
                payload = {"content": message}
            elif "slack.com" in webhook_url:
                payload = {"text": message}
            else:
                # Generic webhook
                payload = {"message": message}
            
            # Send notification
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
            
            logger.info("Notification sent", channel=channel, status=response.status_code)
            
            return {
                "success": True,
                "channel": channel,
                "message_length": len(message),
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("Notification failed", error=str(e), status=e.response.status_code)
            raise ToolError(f"Webhook request failed: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error("Notification failed", error=str(e))
            raise ToolError(f"Failed to send notification: {str(e)}")
