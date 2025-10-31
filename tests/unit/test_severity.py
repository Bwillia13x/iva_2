"""Tests for severity calculation module."""
import json
import tempfile
from datetime import timezone
from pathlib import Path

from src.iva.reconcile.severity import score_severity

# Mock UTC for compatibility
UTC = timezone.utc


def test_severity_licensing_high():
    """Test high severity for licensing with strong evidence."""
    severity, confidence = score_severity("licensing", "underlicensed_vs_claim", 0.7)
    assert severity == "high"
    assert 0.5 <= confidence <= 1.0


def test_severity_licensing_med():
    """Test medium severity for licensing with moderate evidence."""
    severity, confidence = score_severity("licensing", "underlicensed_vs_claim", 0.4)
    assert severity == "med"
    assert 0.4 <= confidence <= 1.0


def test_severity_security_med():
    """Test medium severity for security claims."""
    severity, confidence = score_severity("security", "soc2_unsubstantiated", 0.6)
    assert severity == "med"
    assert 0.4 <= confidence <= 1.0


def test_severity_security_low():
    """Test low severity for security claims with weak evidence."""
    severity, confidence = score_severity("security", "soc2_unsubstantiated", 0.3)
    assert severity == "low"
    assert 0.3 <= confidence <= 1.0


def test_severity_financial_performance_high():
    """Test high severity for financial performance claims."""
    severity, confidence = score_severity("financial_performance", "revenue_claim_unverified", 0.6)
    assert severity == "high"
    assert 0.5 <= confidence <= 1.0


def test_severity_litigation_high():
    """Test high severity for litigation claims."""
    severity, confidence = score_severity("litigation", "litigation_claim_missing_filing", 0.6)
    assert severity == "high"
    assert 0.5 <= confidence <= 1.0


def test_severity_marketing_low():
    """Test low severity for marketing claims."""
    severity, confidence = score_severity("marketing", "vague_marketing_claim", 0.3)
    assert severity == "low"
    assert 0.3 <= confidence <= 1.0


def test_severity_forward_looking_med():
    """Test medium severity for forward-looking statements."""
    severity, confidence = score_severity(
        "forward_looking", "forward_looking_missing_disclaimer", 0.5
    )
    assert severity == "med"
    assert 0.4 <= confidence <= 1.0


def test_severity_with_adjustments():
    """Test that rule adjustments affect severity scoring."""
    # Create temporary adjustments file
    adjustments_data = {
        "adjustments": {
            "underlicensed_vs_claim": {"threshold_shift": -0.2, "confidence_shift": 0.1}
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        feedback_dir = Path(tmpdir) / "data" / "feedback"
        feedback_dir.mkdir(parents=True)
        adjustments_file = feedback_dir / "rule_adjustments.json"
        adjustments_file.write_text(json.dumps(adjustments_data))

        # Temporarily override the path
        import src.iva.reconcile.severity as severity_module

        original_load = severity_module._load_rule_adjustments

        def mock_load():
            return adjustments_data.get("adjustments", {})

        severity_module._load_rule_adjustments = mock_load
        severity_module._ADJUSTMENTS = mock_load()

        try:
            severity, confidence = score_severity("licensing", "underlicensed_vs_claim", 0.4)
            # Lower threshold should result in high severity
            assert severity == "high"
        finally:
            # Restore original function
            severity_module._load_rule_adjustments = original_load
            severity_module._ADJUSTMENTS = original_load()
