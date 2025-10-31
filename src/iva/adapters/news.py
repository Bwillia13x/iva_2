from datetime import UTC, datetime

from ..models.sources import AdapterFinding, Citation


async def search_press(company: str, partner_bank: str | None = None) -> list[AdapterFinding]:
    # Stub: In production, use Bing/SerpAPI or internal news index.
    # We simulate "no press release" for MVP.
    return [
        AdapterFinding(
            key="press_partner_announcement",
            value="",
            status="not_found",
            adapter="news",
            observed_at=datetime.now(UTC),
            snippet="No press article confirming the partnership was located (stub search).",
            citations=[
                Citation(
                    source="News search (stub)",
                    url="https://news.google.com/",
                    query=f"{company} {partner_bank or 'sponsor bank'} partnership",
                    accessed_at=datetime.now(UTC),
                    note="MVP stub",
                )
            ],
        )
    ]
