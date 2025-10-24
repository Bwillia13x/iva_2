from datetime import datetime, UTC
from ..models.sources import AdapterFinding, Citation

async def check_edgar(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="sec_filings_recent",
            value="0",
            status="unknown",
            adapter="edgar",
            observed_at=datetime.now(UTC),
            snippet="EDGAR search returned no public filings; entity may be private or filings unavailable.",
            citations=[Citation(
                source="SEC EDGAR (stub)",
                url="https://www.sec.gov/edgar/search/",
                query=f"company:{company}",
                accessed_at=datetime.now(UTC),
                note="MVP stub"
            )]
        )
    ]
