from datetime import datetime, UTC
from ..models.sources import AdapterFinding, Citation

async def check_edgar(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="sec_filings_recent",
            value="0",
            status="not_found",
            adapter="edgar",
            observed_at=datetime.now(UTC),
            snippet="No recent SEC filings found in stub data.",
            citations=[Citation(
                source="SEC EDGAR (stub)",
                url="https://www.sec.gov/edgar/search/",
                query=f"company:{company}",
                accessed_at=datetime.now(UTC),
                note="MVP stub"
            )]
        )
    ]
