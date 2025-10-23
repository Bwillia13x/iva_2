from datetime import datetime
from ..models.sources import AdapterFinding, Citation

async def check_fintrac(company: str) -> list[AdapterFinding]:
    return [
        AdapterFinding(
            key="fintrac_registered",
            value="false",
            status="not_found",
            citations=[Citation(
                source="FINTRAC MSB Registry (stub)",
                url="https://msb-registrar-recherche.fintrac-canafe.gc.ca/",
                query=f"company:{company}",
                accessed_at=datetime.utcnow(),
                note="MVP stub"
            )]
        )
    ]
