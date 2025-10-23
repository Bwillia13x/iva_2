from datetime import datetime
from ..models.sources import AdapterFinding, Citation

async def search_press(company: str, partner_bank: str | None = None) -> list[AdapterFinding]:
    # Stub: In production, use Bing/SerpAPI or internal news index.
    # We simulate "no press release" for MVP.
    return [
        AdapterFinding(
            key="press_partner_announcement",
            value="",
            status="not_found",
            citations=[Citation(
                source="News search (stub)",
                url="https://news.google.com/",
                query=f"{company} {partner_bank or 'sponsor bank'} partnership",
                accessed_at=datetime.utcnow(),
                note="MVP stub"
            )]
        )
    ]
