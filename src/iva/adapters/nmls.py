from datetime import datetime
from ..models.sources import AdapterFinding, Citation

async def check_nmls(company: str) -> list[AdapterFinding]:
    # MVP stub: In production, implement NMLS Consumer Access scraping/search with consent and respect for TOS.
    # Return sample data to exercise the pipeline.
    return [
        AdapterFinding(
            key="us_mtl_states",
            value="['CA','NY','TX','WA','IL','FL','MA','CO','VA','PA','OH','NJ','GA','AZ']",
            status="confirmed",
            citations=[Citation(
                source="NMLS Consumer Access (stub)",
                url="https://nmlsconsumeraccess.org/",
                query=f"company:{company}",
                accessed_at=datetime.utcnow(),
                note="MVP stub"
            )]
        )
    ]
