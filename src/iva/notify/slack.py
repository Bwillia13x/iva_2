import os, json, asyncio, httpx
from typing import Optional
from ..config import settings
from ..models.recon import TruthCard

def _severity_emoji(sev: str) -> str:
    return {"high":"🛑","med":"⚠️","low":"ℹ️"}.get(sev,"ℹ️")

def card_to_blocks(card: TruthCard):
    blocks = [
      {"type":"header","text":{"type":"plain_text","text":f"Iva • Truth Meter for {card.company}","emoji":True}},
      {"type":"context","elements":[{"type":"mrkdwn","text":f"<{card.url}|{card.url}> • {card.severity_summary} • Confidence {round(card.overall_confidence*100)}% • Generated {card.generated_at.isoformat()}"}]},
    ]
    for d in card.discrepancies[:5]:
        followups = "; ".join(d.explanation.follow_up_actions) if d.explanation.follow_up_actions else "None"
        provenance = "; ".join([f"{p.adapter} @ {p.observed_at.date()}" for p in d.provenance]) or "n/a"
        evidence = "; ".join([f"{e.adapter}:{e.finding_key}" for e in d.explanation.supporting_evidence]) or "n/a"
        related = ", ".join(d.related_claims) if d.related_claims and len(d.related_claims) > 1 else None
        notes = d.explanation.notes.strip() if d.explanation.notes else ""
        lines = [
            f"*Claim ID:* `{d.claim_id}`",
            f"*Why it matters:* {d.why_it_matters}",
            f"*Expected evidence:* {d.expected_evidence}",
            f"*Verdict:* {d.explanation.verdict} ({round(d.explanation.confidence*100)}%)",
            f"*Follow-ups:* {followups}",
            f"*Evidence:* {evidence}",
            f"*Provenance:* {provenance}",
        ]
        if related:
            lines.insert(1, f"*Related claims:* {related}")
        if notes:
            lines.insert(4, f"*Notes:* {notes}")
        text = "\n".join(lines)
        blocks.append({
            "type":"section",
            "text":{"type":"mrkdwn","text":f"{_severity_emoji(d.severity)} *{d.type}* • Sev: *{d.severity}* • Conf: {round(d.confidence*100)}%\n{text}"}
        })
    return blocks

async def post_slack(card: TruthCard, channel: Optional[str]=None):
    webhook = settings.slack_webhook_url
    if webhook:
        async with httpx.AsyncClient() as client:
            payload = {"text": f"Iva Truth Meter: {card.company}", "blocks": card_to_blocks(card)}
            r = await client.post(webhook, json=payload, timeout=20)
            r.raise_for_status()
    else:
        # No webhook, print JSON for demo
        print(json.dumps({"blocks": card_to_blocks(card)}, indent=2))
