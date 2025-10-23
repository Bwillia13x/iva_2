from datetime import datetime
from ..models.sources import AdapterFinding, Citation

async def check_edgar(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="sec_filings_recent",
            value="0",
            status="not_found",
            citations=[Citation(
                source="SEC EDGAR (stub)",
                url="https://www.sec.gov/edgar/search/",
                query=f"company:{company}",
                accessed_at=datetime.utcnow(),
                note="MVP stub"
            )]
        )
    ]
