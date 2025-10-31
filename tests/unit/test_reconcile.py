from datetime import datetime, timezone

from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.engine import reconcile

UTC = timezone.utc


def test_reconcile_underlicensed():
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="1", category="licensing", claim_text="Licensed in 30 states", values=["30"]
            )
        ],
    )
    adapters = {
        "nmls": [
            AdapterFinding(
                key="us_mtl_states",
                value="['CA','NY']",
                status="confirmed",
                adapter="nmls",
                observed_at=datetime.now(UTC),
                snippet="Stub NMLS states coverage sample.",
                citations=[Citation(source="t", url="u", query="q", accessed_at=datetime.now(UTC))],
            )
        ]
    }
    card = reconcile(cs, adapters)
    discrepancy = next(d for d in card.discrepancies if d.type == "underlicensed_vs_claim")
    assert discrepancy.explanation.verdict == "needs_review"
    assert discrepancy.provenance and discrepancy.provenance[0].adapter == "nmls"
    assert discrepancy.explanation.supporting_evidence[0].summary
    assert discrepancy.related_claims == ["1"]


def test_marketing_discrepancy_deduplicates_claims():
    cs = ClaimSet(
        url="u",
        company="c",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(
                id="m1",
                category="marketing",
                claim_text="Millions of customers use us",
                claim_kind="customer_count",
            ),
            ExtractedClaim(
                id="m2",
                category="marketing",
                claim_text="We process hundreds of billions",
                claim_kind="transaction_volume",
            ),
        ],
    )
    edgar_finding = AdapterFinding(
        key="sec_filings_recent",
        value="0",
        status="unknown",
        adapter="edgar",
        observed_at=datetime.now(UTC),
        snippet="No filings located",
        citations=[
            Citation(
                source="EDGAR", url="https://sec.gov", query="q", accessed_at=datetime.now(UTC)
            )
        ],
    )
    news_finding = AdapterFinding(
        key="press_partner_announcement",
        value="",
        status="not_found",
        adapter="news",
        observed_at=datetime.now(UTC),
        snippet="No press hits",
        citations=[
            Citation(
                source="News",
                url="https://news.google.com",
                query="q",
                accessed_at=datetime.now(UTC),
            )
        ],
    )
    adapters = {
        "edgar": [edgar_finding],
        "news": [news_finding],
        "press_metrics": [],
    }
    card = reconcile(cs, adapters)
    marketing = [d for d in card.discrepancies if d.type == "marketing_metric_unverified"]
    assert len(marketing) == 1
    assert set(marketing[0].related_claims) == {"m1", "m2"}
    assert set(marketing[0].related_claim_texts) == {
        "Millions of customers use us",
        "We process hundreds of billions",
    }
    assert "Also flagged claim" in (marketing[0].explanation.notes or "")
