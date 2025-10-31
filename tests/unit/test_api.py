"""Tests for API endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.iva.server import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Iva Truth Meter"


def test_home_endpoint():
    """Test home page endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@patch("src.iva.server._verify")
def test_api_verify_endpoint(mock_verify):
    """Test API verify endpoint."""
    from datetime import datetime, timezone

    from src.iva.models.recon import TruthCard

    UTC = timezone.utc

    # Mock the verify function
    mock_card = TruthCard(
        url="http://test.com",
        company="Test Company",
        severity_summary="H:0 • M:0 • L:0",
        discrepancies=[],
        overall_confidence=0.8,
        generated_at=datetime.now(UTC),
    )
    mock_verify.return_value = (mock_card, "<html>Memo</html>")

    response = client.post(
        "/api/v1/verify",
        json={"url": "http://test.com", "company": "Test Company", "jurisdiction": "US"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["truth_card"]["company"] == "Test Company"


@patch("src.iva.server._verify")
def test_api_verify_timeout(mock_verify):
    """Test API verify endpoint with timeout."""
    import asyncio

    async def timeout_verify(*args, **kwargs):
        await asyncio.sleep(130)  # Longer than 120s timeout

    mock_verify.side_effect = asyncio.TimeoutError()

    response = client.post(
        "/api/v1/verify",
        json={"url": "http://test.com", "company": "Test Company", "jurisdiction": "US"},
    )

    assert response.status_code == 408


@patch("src.iva.alerts.monitor.AlertManager")
def test_api_get_alerts(mock_alert_manager):
    """Test get alerts endpoint."""
    from datetime import datetime, timezone

    from src.iva.alerts.monitor import Alert, AlertSeverity, AlertType

    UTC = timezone.utc

    mock_manager = mock_alert_manager.return_value
    mock_manager.load_alerts.return_value = [
        Alert(
            id="alert1",
            company="Test Company",
            alert_type=AlertType.NEW_HIGH_SEVERITY_DISCREPANCY,
            severity=AlertSeverity.HIGH,
            message="Test alert",
            details={},
            generated_at=datetime.now(UTC),
        )
    ]

    response = client.get("/api/v1/alerts/Test Company")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["company"] == "Test Company"
    assert len(data["alerts"]) == 1


@patch("src.iva.alerts.monitor.AlertManager")
def test_api_acknowledge_alert(mock_alert_manager):
    """Test acknowledge alert endpoint."""
    mock_manager = mock_alert_manager.return_value
    mock_manager.acknowledge_alert.return_value = True

    response = client.post("/api/v1/alerts/Test Company/alert1/acknowledge")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@patch("src.iva.alerts.monitor.AlertManager")
def test_api_acknowledge_alert_not_found(mock_alert_manager):
    """Test acknowledge alert endpoint with non-existent alert."""
    mock_manager = mock_alert_manager.return_value
    mock_manager.acknowledge_alert.return_value = False

    response = client.post("/api/v1/alerts/Test Company/nonexistent/acknowledge")

    assert response.status_code == 404


@patch("src.iva.server._verify")
@patch("src.iva.export.pdf.generate_pdf")
def test_api_export_pdf(mock_pdf, mock_verify):
    """Test PDF export endpoint."""
    from datetime import datetime, timezone

    from src.iva.models.recon import TruthCard

    UTC = timezone.utc

    mock_card = TruthCard(
        url="http://test.com",
        company="Test Company",
        severity_summary="H:0 • M:0 • L:0",
        discrepancies=[],
        overall_confidence=0.8,
        generated_at=datetime.now(UTC),
    )
    mock_verify.return_value = (mock_card, "<html>Memo</html>")
    mock_pdf.return_value = b"PDF content"

    response = client.get("/api/v1/truth-card/Test Company/pdf?url=http://test.com")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert b"PDF content" in response.content


def test_api_verify_request_validation():
    """Test API verify endpoint request validation."""
    # Missing required fields
    response = client.post(
        "/api/v1/verify",
        json={
            "url": "http://test.com"
            # Missing company
        },
    )

    assert response.status_code == 422  # Validation error


@patch("src.iva.server._verify")
def test_api_verify_with_alerts(mock_verify):
    """Test API verify endpoint with alert generation."""
    from datetime import datetime, timezone

    from src.iva.models.recon import Discrepancy, ExplanationBundle, TruthCard

    UTC = timezone.utc

    discrepancy = Discrepancy(
        claim_id="claim1",
        type="test_discrepancy",
        severity="high",
        confidence=0.8,
        why_it_matters="Test",
        expected_evidence="Test",
        findings=[],
        claim_text="Test",
        explanation=ExplanationBundle(
            verdict="escalate", supporting_evidence=[], confidence=0.8, follow_up_actions=[]
        ),
        provenance=[],
    )

    mock_card = TruthCard(
        url="http://test.com",
        company="Test Company",
        severity_summary="H:1 • M:0 • L:0",
        discrepancies=[discrepancy],
        overall_confidence=0.8,
        generated_at=datetime.now(UTC),
    )
    mock_verify.return_value = (mock_card, "<html>Memo</html>")

    response = client.post(
        "/api/v1/verify",
        json={
            "url": "http://test.com",
            "company": "Test Company",
            "jurisdiction": "US",
            "generate_alerts": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "alerts_generated" in data
