"""
Automated alerts system for material changes.

Monitors for significant changes in claims, discrepancies, or financial metrics
and generates alerts when material changes are detected.
"""

from .monitor import Alert, AlertManager, AlertRule, AlertSeverity, AlertType
from .notifications import send_alert

__all__ = ["AlertManager", "AlertRule", "AlertSeverity", "Alert", "AlertType", "send_alert"]
