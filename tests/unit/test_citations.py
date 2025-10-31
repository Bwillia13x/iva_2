"""Tests for citation confidence calculation."""
from datetime import datetime, timezone

from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.citations import confidence_from_findings

UTC = timezone.utc


def test_confidence_confirmed_findings():
    """Test confidence calculation with confirmed findings."""
    findings = [
        AdapterFinding(
            key="test_key",
            value="test_value",
            status="confirmed",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[
                Citation(
                    source="test",
                    url="http://test.com",
                    query="test",
                    accessed_at=datetime.now(UTC),
                )
            ],
        ),
        AdapterFinding(
            key="test_key2",
            value="test_value2",
            status="confirmed",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        ),
    ]
    confidence = confidence_from_findings(findings)
    assert confidence == 0.5  # 2 confirmed findings * 0.25 = 0.5


def test_confidence_mixed_status():
    """Test confidence with mixed status findings."""
    findings = [
        AdapterFinding(
            key="test_key",
            value="test_value",
            status="confirmed",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        ),
        AdapterFinding(
            key="test_key2",
            value="test_value2",
            status="inconsistent",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        ),
        AdapterFinding(
            key="test_key3",
            value="test_value3",
            status="not_found",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        ),
    ]
    confidence = confidence_from_findings(findings)
    assert confidence == 0.6  # 0.25 + 0.2 + 0.15 = 0.6


def test_confidence_caps_at_one():
    """Test that confidence is capped at 1.0."""
    findings = [
        AdapterFinding(
            key=f"test_key{i}",
            value=f"test_value{i}",
            status="confirmed",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        )
        for i in range(10)
    ]
    confidence = confidence_from_findings(findings)
    assert confidence == 1.0  # 10 * 0.25 = 2.5, capped at 1.0


def test_confidence_empty_findings():
    """Test confidence with empty findings."""
    confidence = confidence_from_findings([])
    assert confidence == 0.0


def test_confidence_unknown_status():
    """Test confidence with unknown status findings."""
    findings = [
        AdapterFinding(
            key="test_key",
            value="test_value",
            status="unknown",
            adapter="test_adapter",
            observed_at=datetime.now(UTC),
            citations=[],
        ),
    ]
    confidence = confidence_from_findings(findings)
    assert confidence == 0.0  # Unknown status doesn't contribute
