import asyncio
import uuid
from datetime import UTC, datetime
from typing import Optional

import typer

from .adapters import bank_partners, cfpb, edgar, fintrac, news, nmls, press_metrics, trust_center
from .ingestion.fetch import fetch_html, fetch_rendered
from .ingestion.parse import html_to_text
from .learning.feedback import (
    AnalystAction,
    FeedbackEntry,
    FeedbackLogger,
    sync_feedback,
)
from .llm.client import json_call
from .models.claims import ClaimSet, ExtractedClaim
from .notify.memo import render_html
from .notify.slack import post_slack
from .reconcile.engine import reconcile

app = typer.Typer()

CLAIMS_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
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
                        ],
                    },
                    "claim_text": {"type": "string"},
                    "entity": {"type": "string"},
                    "jurisdiction": {"type": "string", "enum": ["US", "CA", "EU", "UK", "OTHER"]},
                    "claim_kind": {"type": "string"},
                    "values": {"type": "array", "items": {"type": "string"}},
                    "effective_date": {"type": "string"},
                },
                "required": ["id", "category", "claim_text"],
            },
        }
    },
    "required": ["claims"],
}


@app.command()
def verify(
    url: str,
    company: str,
    jurisdiction: str = "US",
    ticker: str = typer.Option(
        None, "--ticker", "-t", help="Stock ticker symbol for public companies (e.g., AAPL)"
    ),
    render_js: bool = False,
):
    """Verify claims on a company website against authoritative sources."""
    asyncio.run(_verify(url, company, jurisdiction, render_js, emit_slack=True, ticker=ticker))


@app.command("feedback")
def log_feedback(
    card_url: str = typer.Argument(..., help="Truth card URL or identifier under review."),
    company: str = typer.Argument(..., help="Company name shown on the truth card."),
    discrepancy_type: str = typer.Argument(..., help="Discrepancy type being overridden."),
    action: AnalystAction = typer.Argument(
        ..., help="Analyst action (confirm/dismiss/override/escalate)."
    ),
    updated_verdict: str | None = typer.Option(
        None, "--verdict", help="Revised verdict after analyst action."
    ),
    notes: str = typer.Option(
        "", "--notes", "-n", help="Optional analyst note or remediation summary."
    ),
    actor: str = typer.Option(
        "analyst", "--actor", help="Identifier of analyst submitting feedback."
    ),
):
    """
    Record analyst feedback for reconciliation learning loops.
    """
    entry = FeedbackEntry(
        card_url=card_url,
        company=company,
        discrepancy_type=discrepancy_type,
        analyst_action=action,
        actor=actor,
        notes=notes or None,
        updated_verdict=updated_verdict,
    )
    FeedbackLogger().log(entry)
    adjustments = sync_feedback()
    typer.echo(
        f"Feedback logged. Current adjustments for {discrepancy_type}: {adjustments.get(discrepancy_type, {})}"
    )


async def _verify(
    url: str,
    company: str,
    jurisdiction: str,
    render_js: bool,
    emit_slack: bool = True,
    ticker: Optional[str] = None,
):
    html = await (fetch_rendered(url) if render_js else fetch_html(url))
    text = html_to_text(html)
    print(f"\n[DEBUG] Extracted {len(text)} chars from {url}")

    with open("src/iva/llm/prompts/extract_claims.prompt") as f:
        prompt_template = f.read()
    prompt = (
        prompt_template
        + f"\n\nURL: {url}\nCompany: {company}\nJurisdiction: {jurisdiction}\n\nCONTENT:\n{text[:12000]}"
    )
    print(f"[DEBUG] Sending {len(prompt)} chars to LLM for claim extraction...")

    raw = json_call(prompt, CLAIMS_SCHEMA)
    print(f"[DEBUG] LLM extracted {len(raw.get('claims', []))} claims")

    claims = []
    seen_claims = set()  # Track claim fingerprints to deduplicate
    
    for c in raw.get("claims", []):
        # Required fields per schema - but handle gracefully if LLM returns malformed data
        if "category" not in c or "claim_text" not in c:
            print(f"[WARN] Skipping malformed claim: {c}")
            continue
        
        # Deduplication: Create fingerprint from normalized claim text
        claim_fingerprint = (
            c["category"],
            c["claim_text"].lower().strip(),
            c.get("claim_kind", "").lower().strip(),
        )
        
        if claim_fingerprint in seen_claims:
            print(f"[DEDUP] Skipping duplicate claim: {c['claim_text'][:60]}...")
            continue
        
        seen_claims.add(claim_fingerprint)
        
        claims.append(
            ExtractedClaim(
                id=c.get("id") or str(uuid.uuid4()),
                category=c["category"],
                claim_text=c["claim_text"],
                entity=c.get("entity"),
                jurisdiction=c.get("jurisdiction"),
                claim_kind=c.get("claim_kind"),
                values=c.get("values"),
                effective_date=c.get("effective_date"),
                citations=[],
            )
        )
    
    print(f"[DEBUG] After deduplication: {len(claims)} unique claims")
    claimset = ClaimSet(url=url, company=company, extracted_at=datetime.now(UTC), claims=claims)

    print(f"\n[DEBUG] Created ClaimSet with {len(claims)} claims:")
    for i, cl in enumerate(claims[:5], 1):
        print(f"  {i}. [{cl.category}] {cl.claim_text[:80]}...")

    # Adapters
    print(f"\n[DEBUG] Running verification adapters...")

    # Import Phase 3 adapters
    # Import Phase 4 adapters
    from .adapters import (
        analyst_coverage,
        earnings_calls,
        edgar_filings,
        historical_tracking,
        peer_comparison,
        press_releases,
    )

    # Run Phase 3 adapters (only for public companies with ticker)
    phase3_adapters = {}
    if ticker:
        phase3_adapters = {
            "earnings_calls": await earnings_calls.check_earnings_calls(company, ticker=ticker),
            "press_releases": await press_releases.check_press_releases(company, ticker=ticker),
            "analyst_coverage": await analyst_coverage.check_analyst_coverage(
                company, ticker=ticker
            ),
            "peer_comparison": await peer_comparison.check_peer_comparison(company, ticker=ticker),
        }

    # Always run historical tracking (works for all companies)
    historical_findings = await historical_tracking.get_claim_history_summary(company)
    phase3_adapters["historical_tracking"] = historical_findings

    # Save current claim set for historical tracking
    historical_tracking.save_claim_set(claimset)

    adapters = {
        "nmls": await nmls.check_nmls(company),
        "fintrac": await fintrac.check_fintrac(company),
        "edgar": await edgar.check_edgar(company),
        "edgar_filings": await edgar_filings.check_edgar_filings(company, ticker=ticker)
        if ticker
        else [],
        "cfpb": await cfpb.check_cfpb(company),
        "bank_partners": await bank_partners.check_bank_partners(company),
        "trust_center": await trust_center.check_trust_center(url),
        "news": await news.search_press(company),
        "press_metrics": await press_metrics.check_press_metrics(company),
        **phase3_adapters,  # Merge Phase 3 adapters
    }

    for adapter_name, results in adapters.items():
        print(f"  - {adapter_name}: {len(results)} findings")

    print(f"\n[DEBUG] Reconciling claims against adapter findings...")
    card = reconcile(claimset, adapters)
    print(f"[DEBUG] Found {len(card.discrepancies)} discrepancies")

    # Phase 4: Generate alerts for material changes
    from .alerts.monitor import AlertManager
    from .alerts.notifications import send_alert

    alert_manager = AlertManager()
    alerts = alert_manager.process_truth_card(card)

    if alerts:
        print(f"[DEBUG] Generated {len(alerts)} alerts")
        # Send critical/high severity alerts
        for alert in alerts:
            if alert.severity.value in ["critical", "high"]:
                await send_alert(alert)

    if emit_slack:
        await post_slack(card)
    memo_html = render_html(card)
    print("\n=== Memo HTML Preview ===\n", memo_html)
    return card, memo_html


if __name__ == "__main__":
    app()
