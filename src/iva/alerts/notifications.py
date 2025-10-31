"""
Alert notification system.

Handles sending alerts via various channels (Slack, email, etc.).
"""

from typing import List

from ..alerts.monitor import Alert
from ..notify.slack import post_slack_alert


async def send_alert(alert: Alert, channels: List[str] = None) -> None:
    """
    Send an alert via specified channels.

    Args:
        alert: The alert to send
        channels: List of channel names (e.g., ["slack", "email"])
    """
    if channels is None:
        channels = ["slack"]  # Default to Slack

    for channel in channels:
        if channel == "slack":
            try:
                await post_slack_alert(alert)
            except Exception as e:
                print(f"[ALERTS] Error sending Slack alert: {e}")
        elif channel == "email":
            # Email notification would be implemented here
            print(f"[ALERTS] Email notifications not yet implemented")
        else:
            print(f"[ALERTS] Unknown channel: {channel}")
