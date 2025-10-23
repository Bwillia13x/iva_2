import json, os
from datetime import datetime
from ..models.sources import AdapterFinding, Citation

SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..","data","seeds","bank_partner_pages.json")

async def check_bank_partners(company: str) -> list[AdapterFinding]:
    items = []
    if os.path.exists(SEED):
        data = json.load(open(SEED))
        # naive lookup: in prototype we check known sponsor bank listings
        listed = []
        for bank in data:
            partners = bank.get("partners",[])
            if any(company.lower() in p.lower() for p in partners):
                listed.append(bank["bank"])
        status = "confirmed" if listed else "not_found"
        items.append(AdapterFinding(
            key="sponsor_bank_listed",
            value=", ".join(listed) if listed else "",
            status=status,
            citations=[Citation(
                source="Bank partner pages (seed)",
                url="",
                query=f"company:{company}",
                accessed_at=datetime.utcnow(),
                note="Prototype seed list"
            )]
        ))
    return items
