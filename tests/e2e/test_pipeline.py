from datetime import datetime
from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.reconcile.engine import reconcile

def test_pipeline_minimal():
    cs = ClaimSet(url="https://example.com", company="Acme", extracted_at=datetime.utcnow(), claims=[
        ExtractedClaim(id="1", category="partner_bank", claim_text="Partnered with Bank X")
    ])
    adapters = {"bank_partners": [], "news": []}
    card = reconcile(cs, adapters)
    assert card.company == "Acme"
    assert card.discrepancies
