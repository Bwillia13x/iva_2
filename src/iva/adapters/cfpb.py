"""
Real CFPB Adapter using the Consumer Complaint Database API.

Endpoint: https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/
"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import httpx

from ..models.sources import AdapterFinding, Citation

CFPB_API_BASE = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1"
USER_AGENT = "Iva Reality Layer support@iva.app"

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # Be gentle

class CFPBRateLimiter:
    def __init__(self):
        self.last_request = 0.0

    async def wait(self):
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request
        if time_since_last < RATE_LIMIT_DELAY:
            await asyncio.sleep(RATE_LIMIT_DELAY - time_since_last)
        self.last_request = asyncio.get_event_loop().time()

_rate_limiter = CFPBRateLimiter()


async def _cfpb_get(url: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    await _rate_limiter.wait()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def check_cfpb(company: str) -> List[AdapterFinding]:
    """
    Check CFPB database for complaints against the company.
    """
    findings: List[AdapterFinding] = []
    now = datetime.now(UTC)

    try:
        # Search for company complaints
        # We use the search API with company param
        print(f"[CFPB] Searching for complaints against {company}")

        # First, try to fuzzy match the company name using suggestion endpoint if possible,
        # or just search directly. The API supports a 'company' filter but it needs exact match usually.
        # Let's try searching first.

        params = {
            "search_term": company,
            "field": "company", # Search in company field
            "size": 5,
            "sort": "relevance_desc"
        }

        data = await _cfpb_get(f"{CFPB_API_BASE}/", params=params)

        hits = data.get("hits", {}).get("hits", [])
        total_hits = data.get("hits", {}).get("total", {}).get("value", 0)

        if total_hits > 0:
            # We found something. Let's see if the company name matches reasonably well.
            # We'll take the first hit's company name as the canonical one if it looks close.
            top_hit = hits[0]["_source"]
            matched_company = top_hit.get("company")

            findings.append(
                AdapterFinding(
                    key="cfpb_complaints_found",
                    value=str(total_hits),
                    status="confirmed",
                    adapter="cfpb",
                    observed_at=now,
                    snippet=f"Found {total_hits} consumer complaints matching '{company}'. Top match: {matched_company}.",
                    citations=[
                        Citation(
                            source="CFPB Consumer Complaint Database",
                            url=f"https://www.consumerfinance.gov/data-research/consumer-complaints/search/?searchField=company&searchText={company}",
                            query=f"search_term:{company}",
                            accessed_at=now
                        )
                    ]
                )
            )

            # Check for recent complaints (last 90 days)
            # We can't easily filter by date in the initial loose search without more complex query,
            # but we can check the hits we got.
            recent_count = 0
            for hit in hits:
                date_received = hit["_source"].get("date_received")
                if date_received:
                    # Parse date (ISO format usually YYYY-MM-DD)
                    try:
                        dt = datetime.fromisoformat(date_received).replace(tzinfo=UTC)
                        if (now - dt).days <= 90:
                            recent_count += 1
                    except ValueError:
                        pass

            if recent_count > 0:
                 findings.append(
                    AdapterFinding(
                        key="cfpb_recent_complaints",
                        value=str(recent_count),
                        status="confirmed",
                        adapter="cfpb",
                        observed_at=now,
                        snippet=f"Found {recent_count} complaints in the last 90 days (from top 5 results).",
                         citations=[
                            Citation(
                                source="CFPB Consumer Complaint Database",
                                url=f"https://www.consumerfinance.gov/data-research/consumer-complaints/search/?searchField=company&searchText={company}",
                                query=f"search_term:{company}",
                                accessed_at=now
                            )
                        ]
                    )
                )

        else:
            findings.append(
                AdapterFinding(
                    key="cfpb_complaints_found",
                    value="0",
                    status="confirmed", # Confirmed zero is good
                    adapter="cfpb",
                    observed_at=now,
                    snippet=f"No consumer complaints found matching '{company}'.",
                    citations=[
                        Citation(
                            source="CFPB Consumer Complaint Database",
                            url=f"https://www.consumerfinance.gov/data-research/consumer-complaints/search/?searchField=company&searchText={company}",
                            query=f"search_term:{company}",
                            accessed_at=now
                        )
                    ]
                )
            )

    except Exception as e:
        print(f"[CFPB] Error: {e}")
        findings.append(
            AdapterFinding(
                key="cfpb_error",
                value="error",
                status="error",
                adapter="cfpb",
                observed_at=now,
                snippet=f"Error querying CFPB database: {e}",
                citations=[]
            )
        )

    return findings
