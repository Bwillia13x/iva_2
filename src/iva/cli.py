import asyncio, uuid
from datetime import datetime, UTC
import typer
from .config import settings
from .ingestion.fetch import fetch_html, fetch_rendered
from .ingestion.parse import html_to_text
from .llm.client import json_call
from .models.claims import ClaimSet, ExtractedClaim
from .adapters import nmls, fintrac, edgar, cfpb, bank_partners, trust_center, news, press_metrics
from .reconcile.engine import reconcile
from .notify.slack import post_slack
from .notify.memo import render_html
from .learning.feedback import (
    FeedbackEntry,
    FeedbackLogger,
    AnalystAction,
    sync_feedback,
)

app = typer.Typer()

CLAIMS_SCHEMA = {
  "type":"object",
  "properties":{
    "claims":{"type":"array","items":{
      "type":"object",
      "properties":{
        "id":{"type":"string"},
        "category":{"type":"string","enum":["licensing","regulatory","partner_bank","security","compliance","marketing"]},
        "claim_text":{"type":"string"},
        "entity":{"type":"string"},
        "jurisdiction":{"type":"string","enum":["US","CA","EU","UK","OTHER"]},
        "claim_kind":{"type":"string"},
        "values":{"type":"array","items":{"type":"string"}},
        "effective_date":{"type":"string"}
      },
      "required":["id","category","claim_text"]
    }}
  },
  "required":["claims"]
}

@app.command()
def verify(url: str, company: str, jurisdiction: str = "US", render_js: bool = False):
    # CLI default: emit Slack if configured
    asyncio.run(_verify(url, company, jurisdiction, render_js, emit_slack=True))

@app.command("feedback")
def log_feedback(
    card_url: str = typer.Argument(..., help="Truth card URL or identifier under review."),
    company: str = typer.Argument(..., help="Company name shown on the truth card."),
    discrepancy_type: str = typer.Argument(..., help="Discrepancy type being overridden."),
    action: AnalystAction = typer.Argument(..., help="Analyst action (confirm/dismiss/override/escalate)."),
    updated_verdict: str | None = typer.Option(None, "--verdict", help="Revised verdict after analyst action."),
    notes: str = typer.Option("", "--notes", "-n", help="Optional analyst note or remediation summary."),
    actor: str = typer.Option("analyst", "--actor", help="Identifier of analyst submitting feedback."),
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
    typer.echo(f"Feedback logged. Current adjustments for {discrepancy_type}: {adjustments.get(discrepancy_type, {})}")

async def _verify(url: str, company: str, jurisdiction: str, render_js: bool, emit_slack: bool = True):
    html = await (fetch_rendered(url) if render_js else fetch_html(url))
    text = html_to_text(html)
    print(f"\n[DEBUG] Extracted {len(text)} chars from {url}")
    
    prompt = open("src/iva/llm/prompts/extract_claims.prompt").read() + f"\n\nURL: {url}\nCompany: {company}\nJurisdiction: {jurisdiction}\n\nCONTENT:\n{text[:12000]}"
    print(f"[DEBUG] Sending {len(prompt)} chars to LLM for claim extraction...")
    
    raw = json_call(prompt, CLAIMS_SCHEMA)
    print(f"[DEBUG] LLM extracted {len(raw.get('claims', []))} claims")
    
    claims = []
    for c in raw.get("claims", []):
        claims.append(ExtractedClaim(
            id=c.get("id") or str(uuid.uuid4()),
            category=c["category"],
            claim_text=c["claim_text"],
            entity=c.get("entity"),
            jurisdiction=c.get("jurisdiction"),
            claim_kind=c.get("claim_kind"),
            values=c.get("values"),
            effective_date=c.get("effective_date"),
            citations=[]
        ))
    claimset = ClaimSet(url=url, company=company, extracted_at=datetime.now(UTC), claims=claims)
    
    print(f"\n[DEBUG] Created ClaimSet with {len(claims)} claims:")
    for i, cl in enumerate(claims[:5], 1):
        print(f"  {i}. [{cl.category}] {cl.claim_text[:80]}...")

    # Adapters
    print(f"\n[DEBUG] Running verification adapters...")
    adapters = {
        "nmls": await nmls.check_nmls(company),
        "fintrac": await fintrac.check_fintrac(company),
        "edgar": await edgar.check_edgar(company),
        "cfpb": await cfpb.check_cfpb(company),
        "bank_partners": await bank_partners.check_bank_partners(company),
        "trust_center": await trust_center.check_trust_center(url),
        "news": await news.search_press(company),
        "press_metrics": await press_metrics.check_press_metrics(company),
    }
    
    for adapter_name, results in adapters.items():
        print(f"  - {adapter_name}: {len(results)} findings")

    print(f"\n[DEBUG] Reconciling claims against adapter findings...")
    card = reconcile(claimset, adapters)
    print(f"[DEBUG] Found {len(card.discrepancies)} discrepancies")
    if emit_slack:
        await post_slack(card)
    memo_html = render_html(card)
    print("\n=== Memo HTML Preview ===\n", memo_html)
    return card, memo_html

if __name__ == "__main__":
    app()
