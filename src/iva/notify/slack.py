import os, json, asyncio, httpx
from typing import Optional
from ..config import settings
from ..models.recon import TruthCard

def _severity_emoji(sev: str) -> str:
    return {"high":"🛑","med":"⚠️","low":"ℹ️"}.get(sev,"ℹ️")

def card_to_blocks(card: TruthCard):
    blocks = [
      {"type":"header","text":{"type":"plain_text","text":f"Iva • Truth Meter for {card.company}","emoji":True}},
      {"type":"context","elements":[{"type":"mrkdwn","text":f"<{card.url}|{card.url}> • {card.severity_summary} • Confidence {round(card.overall_confidence*100)}%"}]},
    ]
    for d in card.discrepancies[:5]:
        text = f"*Claim ID:* `{d.claim_id}`\n*Why it matters:* {d.why_it_matters}\n*Expected evidence:* {d.expected_evidence}\n*Findings:* " + "; ".join([f"{f.key}={f.value} ({f.status})" for f in d.findings])
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
