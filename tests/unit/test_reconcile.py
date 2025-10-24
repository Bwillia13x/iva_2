from datetime import datetime, UTC
from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.engine import reconcile

def test_reconcile_underlicensed():
    cs = ClaimSet(url="u", company="c", extracted_at=datetime.now(UTC), claims=[
        ExtractedClaim(id="1", category="licensing", claim_text="Licensed in 30 states", values=["30"])])
    adapters = {"nmls": [AdapterFinding(
        key="us_mtl_states",
        value="['CA','NY']",
        status="confirmed",
        adapter="nmls",
        observed_at=datetime.now(UTC),
        snippet="Stub NMLS states coverage sample.",
        citations=[Citation(source="t", url="u", query="q", accessed_at=datetime.now(UTC))]
    )]}
    card = reconcile(cs, adapters)
    discrepancy = next(d for d in card.discrepancies if d.type=="underlicensed_vs_claim")
    assert discrepancy.explanation.verdict == "needs_review"
    assert discrepancy.provenance and discrepancy.provenance[0].adapter == "nmls"
    assert discrepancy.explanation.supporting_evidence[0].summary
