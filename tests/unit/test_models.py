"""Tests for model validation and serialization."""
from datetime import datetime, timezone

from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.recon import Discrepancy, EvidencePointer, ExplanationBundle, TruthCard
from src.iva.models.sources import AdapterFinding, Citation

UTC = timezone.utc


def test_claim_model_defaults():
    """Test ExtractedClaim model with defaults."""
    claim = ExtractedClaim(id="test1", category="licensing", claim_text="Test claim")
    assert claim.confidence == 0.6
    assert claim.citations == []
    assert claim.entity is None
    assert claim.jurisdiction is None


def test_claim_model_full():
    """Test ExtractedClaim model with all fields."""
    claim = ExtractedClaim(
        id="test2",
        category="marketing",
        claim_text="Test claim",
        entity="Test Entity",
        jurisdiction="US",
        claim_kind="customer_count",
        values=["10M"],
        effective_date="2024-01-01",
        confidence=0.9,
    )
    assert claim.entity == "Test Entity"
    assert claim.jurisdiction == "US"
    assert claim.values == ["10M"]


def test_claimset_model():
    """Test ClaimSet model."""
    claims = [
        ExtractedClaim(id="1", category="licensing", claim_text="Claim 1"),
        ExtractedClaim(id="2", category="marketing", claim_text="Claim 2"),
    ]
    claimset = ClaimSet(
        url="http://test.com", company="Test Company", extracted_at=datetime.now(UTC), claims=claims
    )
    assert len(claimset.claims) == 2
    assert claimset.url == "http://test.com"
    assert claimset.company == "Test Company"


def test_adapter_finding_model():
    """Test AdapterFinding model."""
    citation = Citation(
        source="Test Source",
        url="http://test.com",
        query="test query",
        accessed_at=datetime.now(UTC),
    )
    finding = AdapterFinding(
        key="test_key",
        value="test_value",
        status="confirmed",
        adapter="test_adapter",
        observed_at=datetime.now(UTC),
        snippet="Test snippet",
        citations=[citation],
    )
    assert finding.key == "test_key"
    assert finding.status == "confirmed"
    assert len(finding.citations) == 1


def test_discrepancy_model():
    """Test Discrepancy model."""
    explanation = ExplanationBundle(
        verdict="needs_review",
        supporting_evidence=[],
        confidence=0.7,
        follow_up_actions=["Action 1", "Action 2"],
    )
    discrepancy = Discrepancy(
        claim_id="claim1",
        type="test_discrepancy",
        severity="high",
        confidence=0.7,
        why_it_matters="Test reason",
        expected_evidence="Test evidence",
        findings=[],
        claim_text="Test claim",
        explanation=explanation,
        provenance=[],
        related_claims=["claim1"],
        related_claim_texts=["Test claim"],
    )
    assert discrepancy.severity == "high"
    assert len(explanation.follow_up_actions) == 2


def test_truth_card_model():
    """Test TruthCard model."""
    discrepancy = Discrepancy(
        claim_id="claim1",
        type="test_discrepancy",
        severity="high",
        confidence=0.7,
        why_it_matters="Test",
        expected_evidence="Test",
        findings=[],
        claim_text="Test",
        explanation=ExplanationBundle(
            verdict="escalate", supporting_evidence=[], confidence=0.7, follow_up_actions=[]
        ),
        provenance=[],
    )
    card = TruthCard(
        url="http://test.com",
        company="Test Company",
        severity_summary="H:1 • M:0 • L:0",
        discrepancies=[discrepancy],
        overall_confidence=0.7,
        generated_at=datetime.now(UTC),
    )
    assert len(card.discrepancies) == 1
    assert card.overall_confidence == 0.7


def test_evidence_pointer_model():
    """Test EvidencePointer model."""
    evidence = EvidencePointer(
        adapter="test_adapter",
        finding_key="test_key",
        summary="Test summary",
        citation_urls=["http://test.com"],
    )
    assert evidence.adapter == "test_adapter"
    assert len(evidence.citation_urls) == 1


def test_model_serialization():
    """Test that models can be serialized to dict."""
    claim = ExtractedClaim(id="test1", category="licensing", claim_text="Test claim")
    claim_dict = claim.model_dump()
    assert isinstance(claim_dict, dict)
    assert claim_dict["id"] == "test1"
    assert claim_dict["category"] == "licensing"


def test_claim_category_validation():
    """Test that claim categories are validated."""
    valid_categories = [
        "licensing",
        "regulatory",
        "partner_bank",
        "security",
        "compliance",
        "marketing",
        "financial_performance",
        "market_position",
        "business_metrics",
        "forward_looking",
        "governance",
        "litigation",
        "intellectual_property",
        "material_events",
    ]
    for cat in valid_categories:
        claim = ExtractedClaim(
            id="test",
            category=cat,  # type: ignore
            claim_text="Test",
        )
        assert claim.category == cat


def test_confidence_validation():
    """Test that confidence is validated between 0 and 1."""
    from pydantic import ValidationError

    # Should work with valid values
    claim1 = ExtractedClaim(id="test", category="licensing", claim_text="Test", confidence=0.5)
    assert claim1.confidence == 0.5

    # Should reject values > 1.0 (Pydantic validation)
    try:
        _ = ExtractedClaim(
            id="test2",
            category="licensing",
            claim_text="Test",
            confidence=1.5,  # type: ignore
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass
    
    # Should reject values < 0.0 (Pydantic validation)
    try:
        _ = ExtractedClaim(
            id="test3",
            category="licensing",
            claim_text="Test",
            confidence=-0.5,  # type: ignore
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass

    # Test boundary values
    claim4 = ExtractedClaim(id="test4", category="licensing", claim_text="Test", confidence=1.0)
    assert claim4.confidence == 1.0

    claim5 = ExtractedClaim(id="test5", category="licensing", claim_text="Test", confidence=0.0)
    assert claim5.confidence == 0.0
