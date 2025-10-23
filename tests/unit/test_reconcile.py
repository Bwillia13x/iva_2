from datetime import datetime
from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.engine import reconcile

def test_reconcile_underlicensed():
    cs = ClaimSet(url="u", company="c", extracted_at=datetime.utcnow(), claims=[
        ExtractedClaim(id="1", category="licensing", claim_text="Licensed in 30 states", values=["30"])])
    adapters = {"nmls": [AdapterFinding(
        key="us_mtl_states",
        value="['CA','NY']",
        status="confirmed",
        citations=[Citation(source="t", url="u", query="q", accessed_at=datetime.utcnow())]
    )]}
    card = reconcile(cs, adapters)
    assert any(d.type=="underlicensed_vs_claim" for d in card.discrepancies)
