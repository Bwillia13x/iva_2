"""Tests for alert monitoring system."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.iva.alerts.monitor import Alert, AlertManager, AlertSeverity, AlertType
from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.recon import Discrepancy, ExplanationBundle, TruthCard

UTC = timezone.utc


def test_alert_manager_save_and_load():
    """Test saving and loading alerts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override alerts directory
        import src.iva.alerts.monitor as monitor_module

        original_dir = monitor_module.ALERTS_DATA_DIR
        monitor_module.ALERTS_DATA_DIR = Path(tmpdir) / "data" / "alerts"
        monitor_module.ALERTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            manager = AlertManager()
            alert = Alert(
                id="test_alert_1",
                company="Test Company",
                alert_type=AlertType.NEW_HIGH_SEVERITY_DISCREPANCY,
                severity=AlertSeverity.HIGH,
                message="Test alert message",
                details={"test": "data"},
                generated_at=datetime.now(UTC),
            )

            manager.save_alert(alert)
            loaded_alerts = manager.load_alerts("Test Company")

            assert len(loaded_alerts) == 1
            assert loaded_alerts[0].id == alert.id
            assert loaded_alerts[0].company == alert.company
            assert loaded_alerts[0].message == alert.message
        finally:
            monitor_module.ALERTS_DATA_DIR = original_dir


def test_alert_manager_acknowledge():
    """Test acknowledging alerts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.iva.alerts.monitor as monitor_module

        original_dir = monitor_module.ALERTS_DATA_DIR
        monitor_module.ALERTS_DATA_DIR = Path(tmpdir) / "data" / "alerts"
        monitor_module.ALERTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            manager = AlertManager()
            alert = Alert(
                id="test_alert_2",
                company="Test Company",
                alert_type=AlertType.NEW_HIGH_SEVERITY_DISCREPANCY,
                severity=AlertSeverity.HIGH,
                message="Test alert",
                details={},
                generated_at=datetime.now(UTC),
            )

            manager.save_alert(alert)

            # Acknowledge the alert
            success = manager.acknowledge_alert("Test Company", "test_alert_2")
            assert success

            # Load unacknowledged only
            unacked = manager.load_alerts("Test Company", unacknowledged_only=True)
            assert len(unacked) == 0

            # Load all
            all_alerts = manager.load_alerts("Test Company")
            assert len(all_alerts) == 1
            assert all_alerts[0].acknowledged
        finally:
            monitor_module.ALERTS_DATA_DIR = original_dir


def test_alert_manager_process_truth_card():
    """Test processing truth card to generate alerts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.iva.alerts.monitor as monitor_module

        original_dir = monitor_module.ALERTS_DATA_DIR
        monitor_module.ALERTS_DATA_DIR = Path(tmpdir) / "data" / "alerts"
        monitor_module.ALERTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            manager = AlertManager()

            # Create a truth card with high-severity discrepancy
            claim = ExtractedClaim(
                id="claim1",
                category="litigation",
                claim_text="We have no litigation",
            )
            # Create claimset for context (not directly used but provides structure)
            ClaimSet(
                url="http://test.com",
                company="Test Company",
                extracted_at=datetime.now(UTC),
                claims=[claim],
            )

            discrepancy = Discrepancy(
                claim_id="claim1",
                type="litigation_claim_missing_filing",
                severity="high",
                confidence=0.8,
                why_it_matters="Test reason",
                expected_evidence="Test evidence",
                findings=[],
                claim_text="Test claim",
                explanation=ExplanationBundle(
                    verdict="escalate",
                    supporting_evidence=[],
                    confidence=0.8,
                    follow_up_actions=[],
                ),
                provenance=[],
            )

            card = TruthCard(
                url="http://test.com",
                company="Test Company",
                severity_summary="H:1 • M:0 • L:0",
                discrepancies=[discrepancy],
                overall_confidence=0.8,
                generated_at=datetime.now(UTC),
            )

            alerts = manager.process_truth_card(card)

            # Should generate alert for high-severity discrepancy
            assert len(alerts) > 0
            assert any(a.alert_type == AlertType.NEW_HIGH_SEVERITY_DISCREPANCY for a in alerts)
            assert any(a.severity == AlertSeverity.HIGH for a in alerts)
        finally:
            monitor_module.ALERTS_DATA_DIR = original_dir


def test_alert_manager_material_event():
    """Test alert generation for material event missing filing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.iva.alerts.monitor as monitor_module

        original_dir = monitor_module.ALERTS_DATA_DIR
        monitor_module.ALERTS_DATA_DIR = Path(tmpdir) / "data" / "alerts"
        monitor_module.ALERTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            manager = AlertManager()

            claim = ExtractedClaim(
                id="claim1",
                category="material_events",
                claim_text="Major acquisition",
            )
            # Create claimset for context (not directly used but provides structure)
            ClaimSet(
                url="http://test.com",
                company="Test Company",
                extracted_at=datetime.now(UTC),
                claims=[claim],
            )

            discrepancy = Discrepancy(
                claim_id="claim1",
                type="material_event_missing_8k",
                severity="high",
                confidence=0.9,
                why_it_matters="SEC compliance issue",
                expected_evidence="8-K filing",
                findings=[],
                claim_text="Major acquisition",
                explanation=ExplanationBundle(
                    verdict="escalate",
                    supporting_evidence=[],
                    confidence=0.9,
                    follow_up_actions=[],
                ),
                provenance=[],
            )

            card = TruthCard(
                url="http://test.com",
                company="Test Company",
                severity_summary="H:1 • M:0 • L:0",
                discrepancies=[discrepancy],
                overall_confidence=0.9,
                generated_at=datetime.now(UTC),
            )

            alerts = manager.process_truth_card(card)

            # Should generate critical alert for material event
            assert any(a.alert_type == AlertType.MATERIAL_EVENT_MISSING_FILING for a in alerts)
            assert any(a.severity == AlertSeverity.CRITICAL for a in alerts)
        finally:
            monitor_module.ALERTS_DATA_DIR = original_dir
