from datetime import UTC, datetime

from ..models.sources import AdapterFinding, Citation


async def check_fintrac(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="fintrac_registered",
            value="false",
            status="not_found",
            adapter="fintrac",
            observed_at=datetime.now(UTC),
            snippet="Stubbed FINTRAC lookup returned no registration match.",
            citations=[
                Citation(
                    source="FINTRAC MSB Registry (stub)",
                    url="https://msb-registrar-recherche.fintrac-canafe.gc.ca/",
                    query=f"company:{company}",
                    accessed_at=datetime.now(UTC),
                    note="MVP stub",
                )
            ],
        )
    ]
