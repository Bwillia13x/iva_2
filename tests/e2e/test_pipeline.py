from datetime import datetime, UTC
from pathlib import Path
from src.iva.models.claims import ClaimSet, ExtractedClaim
from src.iva.models.sources import AdapterFinding, Citation
from src.iva.reconcile.engine import reconcile
from src.iva.eval.artifacts import generate_truthcard_artifacts
from src.iva.eval.harness import load_golden, evaluate, EvaluationTier

def test_pipeline_minimal(tmp_path: Path):
    cs = ClaimSet(
        url="https://example.com/acme",
        company="Acme Payments Inc.",
        extracted_at=datetime.now(UTC),
        claims=[
            ExtractedClaim(id="1", category="licensing", claim_text="Licensed in 30 states", values=["30"]),
            ExtractedClaim(id="2", category="partner_bank", claim_text="Partnered with Bank X"),
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
                snippet="Stub NMLS result for minimal test.",
                citations=[
                    Citation(
                        source="NMLS Consumer Access (stub)",
                        url="https://nmlsconsumeraccess.org/",
                        query="company:Acme Payments Inc.",
                        accessed_at=datetime.now(UTC),
                    )
                ],
            )
        ],
        "bank_partners": [
            AdapterFinding(
                key="sponsor_bank_listed",
                value="",
                status="not_found",
                adapter="bank_partners",
                observed_at=datetime.now(UTC),
                snippet="No sponsor bank match in seed dataset (test stub).",
                citations=[
                    Citation(
                        source="Bank partner pages (seed)",
                        url="https://example.com/partners",
                        query="company:Acme Payments Inc.",
                        accessed_at=datetime.now(UTC),
                    )
                ],
            )
        ],
        "news": [
            AdapterFinding(
                key="press_partner_announcement",
                value="",
                status="not_found",
                adapter="news",
                observed_at=datetime.now(UTC),
                snippet="No press announcement located (test stub).",
                citations=[
                    Citation(
                        source="News search (stub)",
                        url="https://news.google.com/",
                        query="Acme Payments Inc. Bank X partnership",
                        accessed_at=datetime.now(UTC),
                    )
                ],
            )
        ],
        "press_metrics": [],
    }
    card = reconcile(cs, adapters)
    assert card.company == "Acme Payments Inc."
    assert card.discrepancies

    artifact_dir = generate_truthcard_artifacts(card, tmp_path / "artifacts")
    assert artifact_dir.exists()

    golden = load_golden()
    unit_report = evaluate([card], golden, tier=EvaluationTier.UNIT)
    assert unit_report.metrics["bundle_completeness"] == 1.0
    assert not unit_report.failures

    regression_report = evaluate([card], golden, tier=EvaluationTier.REGRESSION)
    assert not regression_report.drift_alerts
