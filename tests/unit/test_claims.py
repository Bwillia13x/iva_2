from src.iva.models.claims import ExtractedClaim

def test_claim_model_defaults():
    c = ExtractedClaim(id="1", category="licensing", claim_text="Licensed in 30 states")
    assert 0.0 <= c.confidence <= 1.0
