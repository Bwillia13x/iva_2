"""Additional comprehensive tests for reconciliation engine."""
from datetime import datetime, timezone

from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.engine import reconcile

UTC = timezone.utc


def test_reconcile_security_soc2():
    """Test reconciliation of SOC 2 security claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="security", claim_text="We are SOC 2 Type II certified")
        ],
    )
    adapters = {
        "trust_center": [
            AdapterFinding(
                key="security_txt",
                value="",
                status="not_found",
                adapter="trust_center",
                observed_at=datetime.now(UTC),
                snippet="No security.txt found",
                citations=[Citation(source="t", url="u", query="q", accessed_at=datetime.now(UTC))],
            )
        ]
    }
    card = reconcile(cs, adapters)

    soc2_discs = [d for d in card.discrepancies if d.type == "soc2_unsubstantiated"]
    assert len(soc2_discs) > 0
    assert soc2_discs[0].claim_id == "1"
    assert soc2_discs[0].severity in ["med", "low"]


def test_reconcile_security_iso():
    """Test reconciliation of ISO 27001 security claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[ExtractedClaim(id="1", category="security", claim_text="ISO 27001 certified")],
    )
    adapters = {
        "trust_center": [
            AdapterFinding(
                key="iso_cert",
                value="",
                status="not_found",
                adapter="trust_center",
                observed_at=datetime.now(UTC),
                snippet="No ISO cert found",
                citations=[],
            )
        ]
    }
    card = reconcile(cs, adapters)

    iso_discs = [d for d in card.discrepancies if d.type == "iso_unverified"]
    assert len(iso_discs) > 0
    assert iso_discs[0].claim_id == "1"


def test_reconcile_security_pci():
    """Test reconciliation of PCI DSS security claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="security", claim_text="PCI DSS Level 1 compliant")
        ],
    )
    adapters = {"trust_center": []}
    card = reconcile(cs, adapters)

    pci_discs = [d for d in card.discrepancies if d.type == "pci_requires_verification"]
    assert len(pci_discs) > 0
    assert pci_discs[0].claim_id == "1"


def test_reconcile_regulatory_sec():
    """Test reconciliation of SEC regulatory claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[ExtractedClaim(id="1", category="regulatory", claim_text="Registered with SEC")],
    )
    adapters = {
        "edgar": [
            AdapterFinding(
                key="edgar_search",
                value="",
                status="not_found",
                adapter="edgar",
                observed_at=datetime.now(UTC),
                snippet="No EDGAR filings found",
                citations=[],
            )
        ],
        "cfpb": [],
    }
    card = reconcile(cs, adapters)

    reg_discs = [d for d in card.discrepancies if d.type == "regulatory_claim_unverified"]
    assert len(reg_discs) > 0


def test_reconcile_compliance_aml():
    """Test reconciliation of AML/KYC compliance claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="compliance", claim_text="Robust AML and KYC program")
        ],
    )
    adapters = {"trust_center": [], "edgar": []}
    card = reconcile(cs, adapters)

    aml_discs = [d for d in card.discrepancies if d.type == "compliance_program_mentioned"]
    assert len(aml_discs) > 0


def test_reconcile_compliance_gdpr():
    """Test reconciliation of GDPR/CCPA compliance claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="compliance", claim_text="GDPR and CCPA compliant")
        ],
    )
    adapters = {"trust_center": [], "edgar": []}
    card = reconcile(cs, adapters)

    privacy_discs = [d for d in card.discrepancies if d.type == "privacy_compliance_claim"]
    assert len(privacy_discs) > 0


def test_reconcile_vague_marketing():
    """Test reconciliation of vague marketing claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="marketing", claim_text="Leading fintech platform")
        ],
    )
    adapters = {"edgar": [], "news": [], "press_metrics": []}
    card = reconcile(cs, adapters)

    vague_discs = [d for d in card.discrepancies if d.type == "vague_marketing_claim"]
    assert len(vague_discs) > 0


def test_reconcile_financial_performance_revenue():
    """Test reconciliation of revenue claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="1",
                category="financial_performance",
                claim_text="Annual revenue of $100 million",
                values=["$100 million"],
            )
        ],
    )
    adapters = {
        "edgar_filings": [
            AdapterFinding(
                key="edgar_revenue_annual",
                value="50000000",
                status="confirmed",
                adapter="edgar_filings",
                observed_at=datetime.now(UTC),
                snippet="Revenue from 10-K",
                citations=[],
            )
        ]
    }
    card = reconcile(cs, adapters)

    # Should flag for verification since values don't match
    revenue_discs = [d for d in card.discrepancies if "revenue" in d.type]
    assert len(revenue_discs) > 0


def test_reconcile_financial_performance_profitability():
    """Test reconciliation of profitability claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="1", category="financial_performance", claim_text="Profitable company"
            )
        ],
    )
    adapters = {
        "edgar_filings": [
            AdapterFinding(
                key="edgar_net_income_annual",
                value="-1000000",
                status="confirmed",
                adapter="edgar_filings",
                observed_at=datetime.now(UTC),
                snippet="Net loss from 10-K",
                citations=[],
            )
        ]
    }
    card = reconcile(cs, adapters)

    # Should flag contradiction
    profit_discs = [d for d in card.discrepancies if "profitability" in d.type]
    assert len(profit_discs) > 0
    assert any(d.severity == "high" for d in profit_discs)


def test_reconcile_market_position():
    """Test reconciliation of market position claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="market_position", claim_text="#1 payment processor")
        ],
    )
    adapters = {"edgar_filings": [], "news": []}
    card = reconcile(cs, adapters)

    market_discs = [d for d in card.discrepancies if "market_position" in d.type]
    assert len(market_discs) > 0


def test_reconcile_forward_looking_disclaimer():
    """Test reconciliation of forward-looking statements without disclaimer."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="1",
                category="forward_looking",
                claim_text="We expect to reach $1B revenue next year",
            )
        ],
    )
    adapters = {"edgar_filings": []}
    card = reconcile(cs, adapters)

    fl_discs = [
        d for d in card.discrepancies if "forward_looking" in d.type and "disclaimer" in d.type
    ]
    assert len(fl_discs) > 0


def test_reconcile_litigation_disclosure():
    """Test reconciliation of litigation claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[ExtractedClaim(id="1", category="litigation", claim_text="No pending litigation")],
    )
    adapters = {
        "edgar_filings": [
            AdapterFinding(
                key="edgar_10k_item_3_legal",
                value="",
                status="not_found",
                adapter="edgar_filings",
                observed_at=datetime.now(UTC),
                snippet="Item 3 not found",
                citations=[],
            )
        ]
    }
    card = reconcile(cs, adapters)

    lit_discs = [d for d in card.discrepancies if "litigation" in d.type]
    assert len(lit_discs) > 0
    assert any(d.severity == "high" for d in lit_discs)


def test_reconcile_material_event():
    """Test reconciliation of material event claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="material_events", claim_text="Acquired Company X")
        ],
    )
    adapters = {"edgar_filings": [], "press_releases": []}
    card = reconcile(cs, adapters)

    material_discs = [d for d in card.discrepancies if "material_event" in d.type]
    assert len(material_discs) > 0
    assert any(d.severity == "high" for d in material_discs)


def test_reconcile_business_metrics():
    """Test reconciliation of business metrics claims."""
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="1", category="business_metrics", claim_text="10 million active users"
            )
        ],
    )
    adapters = {"edgar_filings": [], "press_metrics": []}
    card = reconcile(cs, adapters)

    metrics_discs = [d for d in card.discrepancies if "business_metric" in d.type]
    assert len(metrics_discs) > 0


def test_reconcile_truth_card_structure():
    """Test that truth card has correct structure."""
    cs = ClaimSet(
        url="http://test.com",
        company="Test Company",
        extracted_at=datetime.now(UTC),
        claims=[ExtractedClaim(id="1", category="marketing", claim_text="Test claim")],
    )
    adapters = {}
    card = reconcile(cs, adapters)

    assert card.url == cs.url
    assert card.company == cs.company
    assert card.generated_at is not None
    assert isinstance(card.severity_summary, str)
    assert (
        "H:" in card.severity_summary
        or "M:" in card.severity_summary
        or "L:" in card.severity_summary
    )
    assert 0.0 <= card.overall_confidence <= 1.0
