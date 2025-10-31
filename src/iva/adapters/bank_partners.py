import json
import os
from datetime import UTC, datetime

from ..models.sources import AdapterFinding, Citation

SEED = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "..",
    "data",
    "seeds",
    "bank_partner_pages.json",
)


async def check_bank_partners(company: str) -> list[AdapterFinding]:
    items = []
    if os.path.exists(SEED):
        with open(SEED) as f:
            data = json.load(f)
        # naive lookup: in prototype we check known sponsor bank listings
        listed = []
        for bank in data:
            partners = bank.get("partners", [])
            if any(company.lower() in p.lower() for p in partners):
                listed.append(bank["bank"])
        status = "confirmed" if listed else "not_found"
        items.append(
            AdapterFinding(
                key="sponsor_bank_listed",
                value=", ".join(listed) if listed else "",
                status=status,
                adapter="bank_partners",
                observed_at=datetime.now(UTC),
                snippet="Sponsor banks matched in seed dataset: " + ", ".join(listed)
                if listed
                else "No sponsor bank match in seed dataset.",
                citations=[
                    Citation(
                        source="Bank partner pages (seed)",
                        url="",
                        query=f"company:{company}",
                        accessed_at=datetime.now(UTC),
                        note="Prototype seed list",
                    )
                ],
            )
        )
    return items
