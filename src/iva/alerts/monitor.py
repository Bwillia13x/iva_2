"""
Alert monitoring system for material changes.

Tracks changes in truth cards over time and generates alerts when material
changes are detected (new high-severity discrepancies, significant metric changes, etc.).
"""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..models.recon import TruthCard

# Store alerts in data directory
ALERTS_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "alerts"
ALERTS_DATA_DIR.mkdir(parents=True, exist_ok=True)


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertType(str, Enum):
    """Types of alerts"""

    NEW_HIGH_SEVERITY_DISCREPANCY = "new_high_severity_discrepancy"
    SEVERITY_INCREASE = "severity_increase"
    CLAIM_REMOVED = "claim_removed"
    FINANCIAL_METRIC_CHANGE = "financial_metric_change"
    MATERIAL_EVENT_MISSING_FILING = "material_event_missing_filing"
    HISTORICAL_CHANGE = "historical_change"


class AlertRule(BaseModel):
    """Rule for generating alerts"""

    alert_type: AlertType
    severity_threshold: AlertSeverity
    enabled: bool = True


class Alert(BaseModel):
    """Alert object"""

    id: str
    company: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    generated_at: datetime
    truth_card_url: Optional[str] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


class AlertManager:
    """Manages alert generation and storage"""

    def __init__(self):
        self.default_rules = [
            AlertRule(
                alert_type=AlertType.NEW_HIGH_SEVERITY_DISCREPANCY,
                severity_threshold=AlertSeverity.HIGH,
            ),
            AlertRule(
                alert_type=AlertType.SEVERITY_INCREASE,
                severity_threshold=AlertSeverity.MEDIUM,
            ),
            AlertRule(
                alert_type=AlertType.MATERIAL_EVENT_MISSING_FILING,
                severity_threshold=AlertSeverity.CRITICAL,
            ),
        ]

    def _get_alerts_file(self, company: str) -> Path:
        """Get the file path for storing alerts for a company"""
        safe_name = (
            "".join(c for c in company if c.isalnum() or c in (" ", "-", "_"))
            .strip()
            .replace(" ", "_")
        )
        return ALERTS_DATA_DIR / f"{safe_name}_alerts.jsonl"

    def save_alert(self, alert: Alert) -> None:
        """Save an alert to storage"""
        alerts_file = self._get_alerts_file(alert.company)

        record = {
            "id": alert.id,
            "company": alert.company,
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "message": alert.message,
            "details": alert.details,
            "generated_at": alert.generated_at.isoformat(),
            "truth_card_url": alert.truth_card_url,
            "acknowledged": alert.acknowledged,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        }

        try:
            with open(alerts_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[ALERTS] Error saving alert for {alert.company}: {e}")

    def load_alerts(
        self, company: str, limit: int = 100, unacknowledged_only: bool = False
    ) -> List[Alert]:
        """Load alerts for a company"""
        alerts_file = self._get_alerts_file(company)

        if not alerts_file.exists():
            return []

        alerts = []
        with open(alerts_file, "r") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if unacknowledged_only and record.get("acknowledged", False):
                        continue
                    alerts.append(
                        Alert(
                            id=record["id"],
                            company=record["company"],
                            alert_type=AlertType(record["alert_type"]),
                            severity=AlertSeverity(record["severity"]),
                            message=record["message"],
                            details=record["details"],
                            generated_at=datetime.fromisoformat(record["generated_at"]),
                            truth_card_url=record.get("truth_card_url"),
                            acknowledged=record.get("acknowledged", False),
                            acknowledged_at=datetime.fromisoformat(record["acknowledged_at"])
                            if record.get("acknowledged_at")
                            else None,
                        )
                    )

        # Sort by generated_at descending
        alerts.sort(key=lambda x: x.generated_at, reverse=True)
        return alerts[:limit]

    def acknowledge_alert(self, company: str, alert_id: str) -> bool:
        """
        Acknowledge an alert and persist the change.

        Returns True if alert was found and acknowledged, False otherwise.
        """
        alerts_file = self._get_alerts_file(company)

        if not alerts_file.exists():
            return False

        # Read all alerts
        alerts = []
        updated = False
        with open(alerts_file, "r") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record["id"] == alert_id and not record.get("acknowledged", False):
                        record["acknowledged"] = True
                        record["acknowledged_at"] = datetime.now(UTC).isoformat()
                        updated = True
                    alerts.append(record)

        # Write back if updated
        if updated:
            with open(alerts_file, "w") as f:
                for record in alerts:
                    f.write(json.dumps(record) + "\n")

        return updated

    def check_for_alerts(
        self, current_card: TruthCard, previous_card: Optional[TruthCard] = None
    ) -> List[Alert]:
        """
        Check for alerts based on current truth card and optionally compare with previous.

        Returns list of alerts that should be generated.
        """
        alerts: List[Alert] = []
        now = datetime.now(UTC)

        # Check for new high-severity discrepancies
        high_severity_discs = [d for d in current_card.discrepancies if d.severity == "high"]
        if high_severity_discs:
            for disc in high_severity_discs:
                # Check if this is a new discrepancy (would need previous card comparison)
                # For now, generate alert for all high-severity discrepancies
                if not previous_card or not any(
                    d.type == disc.type and d.claim_id == disc.claim_id
                    for d in previous_card.discrepancies
                ):
                    alert = Alert(
                        id=f"{current_card.company}_{disc.type}_{now.timestamp()}",
                        company=current_card.company,
                        alert_type=AlertType.NEW_HIGH_SEVERITY_DISCREPANCY,
                        severity=AlertSeverity.HIGH,
                        message=f"New high-severity discrepancy: {disc.type}",
                        details={
                            "discrepancy_type": disc.type,
                            "claim_id": disc.claim_id,
                            "claim_text": disc.claim_text,
                            "why_it_matters": disc.why_it_matters,
                        },
                        generated_at=now,
                        truth_card_url=current_card.url,
                    )
                    alerts.append(alert)

        # Check for material event missing filing (critical)
        material_event_discs = [
            d
            for d in current_card.discrepancies
            if d.type == "material_event_missing_8k" and d.severity == "high"
        ]
        if material_event_discs:
            for disc in material_event_discs:
                alert = Alert(
                    id=f"{current_card.company}_material_event_{now.timestamp()}",
                    company=current_card.company,
                    alert_type=AlertType.MATERIAL_EVENT_MISSING_FILING,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Material event missing required SEC filing: {disc.claim_text or disc.type}",
                    details={
                        "discrepancy_type": disc.type,
                        "claim_id": disc.claim_id,
                        "claim_text": disc.claim_text,
                        "why_it_matters": disc.why_it_matters,
                    },
                    generated_at=now,
                    truth_card_url=current_card.url,
                )
                alerts.append(alert)

        # If we have previous card, check for severity increases
        if previous_card:
            prev_high_count = len([d for d in previous_card.discrepancies if d.severity == "high"])
            curr_high_count = len([d for d in current_card.discrepancies if d.severity == "high"])

            if curr_high_count > prev_high_count:
                alert = Alert(
                    id=f"{current_card.company}_severity_increase_{now.timestamp()}",
                    company=current_card.company,
                    alert_type=AlertType.SEVERITY_INCREASE,
                    severity=AlertSeverity.MEDIUM,
                    message=f"Severity increase: {prev_high_count} -> {curr_high_count} high-severity discrepancies",
                    details={
                        "previous_high_count": prev_high_count,
                        "current_high_count": curr_high_count,
                        "change": curr_high_count - prev_high_count,
                    },
                    generated_at=now,
                    truth_card_url=current_card.url,
                )
                alerts.append(alert)

        return alerts

    def process_truth_card(self, card: TruthCard) -> List[Alert]:
        """
        Process a truth card and generate alerts.

        This method checks against historical data and generates alerts for material changes.
        """
        alerts = self.check_for_alerts(card)

        # Also check historical tracking for significant changes
        from ..adapters.historical_tracking import compare_claims, load_historical_claims

        historical = load_historical_claims(card.company, limit=2)
        if len(historical) >= 2:
            current_claims = historical[0] if historical else None
            previous_claims = historical[1] if len(historical) >= 2 else None

            if current_claims and previous_claims:
                comparison = compare_claims(current_claims, previous_claims)

                # Alert on significant claim removals
                if len(comparison["removed_claims"]) > 3:
                    alert = Alert(
                        id=f"{card.company}_claims_removed_{datetime.now(UTC).timestamp()}",
                        company=card.company,
                        alert_type=AlertType.CLAIM_REMOVED,
                        severity=AlertSeverity.MEDIUM,
                        message=f"Significant claim removals detected: {len(comparison['removed_claims'])} claims removed",
                        details={
                            "removed_count": len(comparison["removed_claims"]),
                            "removed_claims": [
                                c.claim_text for c in comparison["removed_claims"][:5]
                            ],
                        },
                        generated_at=datetime.now(UTC),
                        truth_card_url=card.url,
                    )
                    alerts.append(alert)

        # Save all alerts
        for alert in alerts:
            self.save_alert(alert)

        return alerts
