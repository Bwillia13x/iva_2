from datetime import UTC, datetime

from ..models.sources import AdapterFinding, Citation


async def check_cfpb(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="cfpb_actions",
            value="none",
            status="confirmed",
            adapter="cfpb",
            observed_at=datetime.now(UTC),
            snippet="No CFPB enforcement actions located for this entity (stub).",
            citations=[
                Citation(
                    source="CFPB (stub)",
                    url="https://www.consumerfinance.gov/enforcement/actions/",
                    query=f"company:{company}",
                    accessed_at=datetime.now(UTC),
                    note="MVP stub",
                )
            ],
        )
    ]
