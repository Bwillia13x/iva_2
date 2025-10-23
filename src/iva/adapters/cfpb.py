from datetime import datetime
from ..models.sources import AdapterFinding, Citation

async def check_cfpb(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="cfpb_actions",
            value="none",
            status="confirmed",
            citations=[Citation(
                source="CFPB (stub)",
                url="https://www.consumerfinance.gov/enforcement/actions/",
                query=f"company:{company}",
                accessed_at=datetime.utcnow(),
                note="MVP stub"
            )]
        )
    ]
