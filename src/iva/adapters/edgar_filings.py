"""
Enhanced SEC EDGAR adapter for public company analysis.

Uses the free SEC EDGAR API to fetch and parse company filings:
- Company submissions and filing history
- 10-K annual reports
- 10-Q quarterly reports  
- 8-K material event filings
- XBRL financial data

API Documentation: https://www.sec.gov/edgar/sec-api-documentation
"""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import httpx

from ..models.sources import AdapterFinding, Citation

# SEC API base URLs
SEC_API_BASE = "https://data.sec.gov"
SEC_EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"

# Required User-Agent per SEC API requirements
USER_AGENT = "Iva Reality Layer support@iva.app"

# Rate limiting: SEC requires max 10 requests/second
RATE_LIMIT_DELAY = 0.11  # 110ms between requests


class SECRateLimiter:
    """Simple rate limiter for SEC API (10 req/sec max)"""

    def __init__(self):
        self.last_request = 0.0

    async def wait(self):
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request
        if time_since_last < RATE_LIMIT_DELAY:
            await asyncio.sleep(RATE_LIMIT_DELAY - time_since_last)
        self.last_request = asyncio.get_event_loop().time()


_rate_limiter = SECRateLimiter()


async def _sec_get(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Make rate-limited GET request to SEC API"""
    await _rate_limiter.wait()

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def lookup_cik(
    company_name: Optional[str] = None, ticker: Optional[str] = None
) -> Optional[str]:
    """
    Look up a company's CIK (Central Index Key) from name or ticker.

    Returns CIK as 10-digit string with leading zeros, or None if not found.

    Examples:
        lookup_cik(ticker="AAPL") -> "0000320193"
        lookup_cik(company_name="Apple Inc") -> "0000320193"
    """
    if not company_name and not ticker:
        return None

    try:
        # Use SEC company tickers JSON (updated daily)
        url = "https://www.sec.gov/files/company_tickers.json"
        data = await _sec_get(url)

        # Convert to list of companies
        companies = list(data.values())

        # Search by ticker (exact match, case-insensitive)
        if ticker:
            ticker_upper = ticker.upper().strip()
            for company in companies:
                if company.get("ticker", "").upper() == ticker_upper:
                    cik_int = company["cik_str"]
                    return f"{cik_int:010d}"

        # Search by company name (fuzzy match)
        if company_name:
            name_lower = company_name.lower().strip()
            # Remove common suffixes for matching
            name_clean = re.sub(
                r"\s+(inc\.|incorporated|corp\.|corporation|ltd\.|limited|llc|plc)\.?$",
                "",
                name_lower,
                flags=re.IGNORECASE,
            )

            for company in companies:
                company_title = company.get("title", "").lower()
                # Try exact match first
                if name_clean in company_title or company_title in name_clean:
                    cik_int = company["cik_str"]
                    return f"{cik_int:010d}"

        return None

    except Exception as e:
        print(f"[EDGAR] CIK lookup failed: {e}")
        return None


async def get_company_submissions(cik: str) -> Optional[Dict[str, Any]]:
    """
    Get company filing history and metadata from SEC submissions API.

    Returns dict with:
    - name: Company name
    - tickers: List of ticker symbols
    - exchanges: List of stock exchanges
    - filings: Recent filing history
    """
    try:
        url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
        return await _sec_get(url)
    except Exception as e:
        print(f"[EDGAR] Failed to get submissions for CIK {cik}: {e}")
        return None


async def get_company_facts(cik: str) -> Optional[Dict[str, Any]]:
    """
    Get all XBRL financial data for a company.

    Returns dict with US-GAAP concepts like:
    - Revenues
    - Assets
    - Liabilities
    - CashAndCashEquivalents
    - etc.
    """
    try:
        url = f"{SEC_API_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        return await _sec_get(url)
    except Exception as e:
        print(f"[EDGAR] Failed to get facts for CIK {cik}: {e}")
        return None


def extract_latest_value(
    facts: Dict[str, Any], concept: str, form_type: str = "10-K"
) -> Optional[Dict[str, Any]]:
    """
    Extract the latest value for a financial concept from XBRL facts.

    Args:
        facts: Company facts dict from get_company_facts()
        concept: US-GAAP concept name (e.g., "Revenues", "Assets")
        form_type: Filing type to filter by (default: 10-K for annual)

    Returns:
        Dict with 'value', 'units', 'end_date', 'filed_date' or None
    """
    try:
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        concept_data = us_gaap.get(concept, {})

        # Get USD units (most common for financial metrics)
        usd_data = concept_data.get("units", {}).get("USD", [])

        # Filter by form type and get most recent
        annual_data = [d for d in usd_data if d.get("form") == form_type]

        if not annual_data:
            # Fallback to any data if no form_type match
            annual_data = usd_data

        if annual_data:
            # Sort by end date descending
            annual_data.sort(key=lambda x: x.get("end", ""), reverse=True)
            latest = annual_data[0]

            return {
                "value": latest.get("val"),
                "units": "USD",
                "end_date": latest.get("end"),
                "filed_date": latest.get("filed"),
                "form": latest.get("form"),
                "fy": latest.get("fy"),  # Fiscal year
                "fp": latest.get("fp"),  # Fiscal period
            }

        return None

    except Exception as e:
        print(f"[EDGAR] Failed to extract {concept}: {e}")
        return None


async def get_latest_filing(cik: str, form_type: str = "10-K") -> Optional[Dict[str, Any]]:
    """
    Get the most recent filing of a specific type.

    Args:
        cik: 10-digit CIK
        form_type: Filing type (10-K, 10-Q, 8-K, etc.)

    Returns:
        Dict with filing metadata and accession number
    """
    try:
        submissions = await get_company_submissions(cik)
        if not submissions:
            return None

        recent_filings = submissions.get("filings", {}).get("recent", {})
        forms = recent_filings.get("form", [])

        # Find first matching form
        for idx, form in enumerate(forms):
            if form == form_type:
                return {
                    "form": form,
                    "filing_date": recent_filings["filingDate"][idx],
                    "accession_number": recent_filings["accessionNumber"][idx],
                    "primary_document": recent_filings["primaryDocument"][idx],
                    "primary_doc_description": recent_filings.get("primaryDocDescription", [])[idx]
                    if idx < len(recent_filings.get("primaryDocDescription", []))
                    else "",
                }

        return None

    except Exception as e:
        print(f"[EDGAR] Failed to get latest {form_type}: {e}")
        return None


async def check_edgar_filings(company: str, ticker: Optional[str] = None) -> list[AdapterFinding]:
    """
    Main adapter function: Check SEC EDGAR filings for a public company.

    This function:
    1. Looks up the company's CIK
    2. Fetches recent filings (10-K, 10-Q, 8-K)
    3. Extracts key financial metrics from XBRL data
    4. Returns findings for reconciliation

    Args:
        company: Company name
        ticker: Stock ticker symbol (optional, helps with lookup)

    Returns:
        List of AdapterFinding objects
    """
    findings: List[AdapterFinding] = []
    now = datetime.now(UTC)

    try:
        # Step 1: Lookup CIK
        print(f"[EDGAR] Looking up CIK for company='{company}', ticker='{ticker}'")
        cik = await lookup_cik(company_name=company, ticker=ticker)

        if not cik:
            search_info = f"company:{company}" + (f", ticker:{ticker}" if ticker else "")
            findings.append(
                AdapterFinding(
                    key="edgar_cik",
                    value="not_found",
                    status="not_found",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"Could not find CIK for company '{company}'"
                    + (f" or ticker '{ticker}'" if ticker else "")
                    + ". Company may be private or use a different name.",
                    citations=[
                        Citation(
                            source="SEC EDGAR Company Tickers",
                            url="https://www.sec.gov/files/company_tickers.json",
                            query=search_info,
                            accessed_at=now,
                        )
                    ],
                )
            )
            return findings

        print(f"[EDGAR] Found CIK: {cik}")

        # Step 2: Get company metadata
        submissions = await get_company_submissions(cik)

        if submissions:
            company_name = submissions.get("name", company)
            tickers = submissions.get("tickers", [])
            exchanges = submissions.get("exchanges", [])

            findings.append(
                AdapterFinding(
                    key="edgar_company_name",
                    value=company_name,
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"Official SEC name: {company_name}. Tickers: {', '.join(tickers)}. Exchanges: {', '.join(exchanges)}.",
                    citations=[
                        Citation(
                            source="SEC EDGAR Submissions API",
                            url=f"{SEC_API_BASE}/submissions/CIK{cik}.json",
                            query=f"CIK:{cik}",
                            accessed_at=now,
                        )
                    ],
                )
            )

        # Step 3: Get latest 10-K (annual report) and extract key sections
        latest_10k = await get_latest_filing(cik, "10-K")

        if latest_10k:
            findings.append(
                AdapterFinding(
                    key="edgar_latest_10k",
                    value=latest_10k["filing_date"],
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"Latest 10-K filed on {latest_10k['filing_date']}. Accession: {latest_10k['accession_number']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-K Filing",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=exclude&count=1",
                            query=f"CIK:{cik}, Form:10-K",
                            accessed_at=now,
                        )
                    ],
                )
            )

            # Add references to key sections in 10-K
            # Item 1A: Risk Factors
            findings.append(
                AdapterFinding(
                    key="edgar_10k_item_1a_risks",
                    value="available",
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"10-K Item 1A (Risk Factors) available in filing dated {latest_10k['filing_date']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-K Item 1A",
                            url=f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={latest_10k['accession_number']}&xbrl_type=v",
                            query=f"CIK:{cik}, Form:10-K, Section:Item 1A Risk Factors",
                            accessed_at=now,
                        )
                    ],
                )
            )

            # Item 3: Legal Proceedings
            findings.append(
                AdapterFinding(
                    key="edgar_10k_item_3_legal",
                    value="available",
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"10-K Item 3 (Legal Proceedings) available in filing dated {latest_10k['filing_date']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-K Item 3",
                            url=f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={latest_10k['accession_number']}&xbrl_type=v",
                            query=f"CIK:{cik}, Form:10-K, Section:Item 3 Legal Proceedings",
                            accessed_at=now,
                        )
                    ],
                )
            )

            # Item 7: MD&A (Management Discussion & Analysis)
            findings.append(
                AdapterFinding(
                    key="edgar_10k_item_7_mda",
                    value="available",
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"10-K Item 7 (MD&A) available in filing dated {latest_10k['filing_date']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-K Item 7",
                            url=f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={latest_10k['accession_number']}&xbrl_type=v",
                            query=f"CIK:{cik}, Form:10-K, Section:Item 7 MD&A",
                            accessed_at=now,
                        )
                    ],
                )
            )

        # Step 4: Get latest 10-Q (quarterly report) and extract key sections
        latest_10q = await get_latest_filing(cik, "10-Q")

        if latest_10q:
            findings.append(
                AdapterFinding(
                    key="edgar_latest_10q",
                    value=latest_10q["filing_date"],
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"Latest 10-Q filed on {latest_10q['filing_date']}. Accession: {latest_10q['accession_number']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-Q Filing",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-Q&dateb=&owner=exclude&count=1",
                            query=f"CIK:{cik}, Form:10-Q",
                            accessed_at=now,
                        )
                    ],
                )
            )

            # Add reference to Item 1A (Risk Factors) in 10-Q
            findings.append(
                AdapterFinding(
                    key="edgar_10q_item_1a_risks",
                    value="available",
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"10-Q Item 1A (Risk Factors) available in filing dated {latest_10q['filing_date']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-Q Item 1A",
                            url=f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={latest_10q['accession_number']}&xbrl_type=v",
                            query=f"CIK:{cik}, Form:10-Q, Section:Item 1A Risk Factors",
                            accessed_at=now,
                        )
                    ],
                )
            )

            # Add reference to Part I Item 2 (MD&A) in 10-Q
            findings.append(
                AdapterFinding(
                    key="edgar_10q_item_2_mda",
                    value="available",
                    status="confirmed",
                    adapter="edgar_filings",
                    observed_at=now,
                    snippet=f"10-Q Part I Item 2 (MD&A) available in filing dated {latest_10q['filing_date']}",
                    citations=[
                        Citation(
                            source="SEC EDGAR 10-Q Item 2",
                            url=f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={latest_10q['accession_number']}&xbrl_type=v",
                            query=f"CIK:{cik}, Form:10-Q, Section:Part I Item 2 MD&A",
                            accessed_at=now,
                        )
                    ],
                )
            )

        # Step 5: Get recent 8-K filings (material events)
        # Fetch last 5 8-K filings to check for recent material events
        if submissions:
            recent_filings = submissions.get("filings", {}).get("recent", {})
            forms = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])
            accession_numbers = recent_filings.get("accessionNumber", [])
            # primary_docs available but not currently used
            # primary_docs = recent_filings.get("primaryDocument", [])

            # Get last 5 8-K filings (material events)
            eight_k_count = 0
            for idx, form in enumerate(forms):
                if form == "8-K" and eight_k_count < 5:
                    filing_date = filing_dates[idx] if idx < len(filing_dates) else ""
                    accession = accession_numbers[idx] if idx < len(accession_numbers) else ""
                    # primary_doc available but not currently used in snippet

                    findings.append(
                        AdapterFinding(
                            key=f"edgar_8k_{eight_k_count + 1}",
                            value=filing_date,
                            status="confirmed",
                            adapter="edgar_filings",
                            observed_at=now,
                            snippet=f"8-K material event filing on {filing_date}. Accession: {accession}",
                            citations=[
                                Citation(
                                    source="SEC EDGAR 8-K Filing",
                                    url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=exclude&count=10",
                                    query=f"CIK:{cik}, Form:8-K, Date:{filing_date}",
                                    accessed_at=now,
                                )
                            ],
                        )
                    )
                    eight_k_count += 1

        # Step 6: Get financial facts (XBRL data)
        facts = await get_company_facts(cik)

        if facts:
            # Extract key financial metrics
            revenue = extract_latest_value(facts, "Revenues", "10-K")
            if revenue:
                findings.append(
                    AdapterFinding(
                        key="edgar_revenue_annual",
                        value=str(revenue["value"]),
                        status="confirmed",
                        adapter="edgar_filings",
                        observed_at=now,
                        snippet=f"Annual revenue: ${revenue['value']:,} ({revenue['end_date']}, filed {revenue['filed_date']})",
                        citations=[
                            Citation(
                                source="SEC EDGAR XBRL Company Facts",
                                url=f"{SEC_API_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
                                query=f"CIK:{cik}, Concept:Revenues",
                                accessed_at=now,
                            )
                        ],
                    )
                )

            # Try RevenueFromContractWithCustomerExcludingAssessedTax as fallback
            if not revenue:
                revenue = extract_latest_value(
                    facts, "RevenueFromContractWithCustomerExcludingAssessedTax", "10-K"
                )
                if revenue:
                    findings.append(
                        AdapterFinding(
                            key="edgar_revenue_annual",
                            value=str(revenue["value"]),
                            status="confirmed",
                            adapter="edgar_filings",
                            observed_at=now,
                            snippet=f"Annual revenue: ${revenue['value']:,} ({revenue['end_date']}, filed {revenue['filed_date']})",
                            citations=[
                                Citation(
                                    source="SEC EDGAR XBRL Company Facts",
                                    url=f"{SEC_API_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
                                    query=f"CIK:{cik}, Concept:RevenueFromContractWithCustomerExcludingAssessedTax",
                                    accessed_at=now,
                                )
                            ],
                        )
                    )

            # Extract assets
            assets = extract_latest_value(facts, "Assets", "10-K")
            if assets:
                findings.append(
                    AdapterFinding(
                        key="edgar_assets_total",
                        value=str(assets["value"]),
                        status="confirmed",
                        adapter="edgar_filings",
                        observed_at=now,
                        snippet=f"Total assets: ${assets['value']:,} ({assets['end_date']})",
                        citations=[
                            Citation(
                                source="SEC EDGAR XBRL Company Facts",
                                url=f"{SEC_API_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
                                query=f"CIK:{cik}, Concept:Assets",
                                accessed_at=now,
                            )
                        ],
                    )
                )

            # Extract net income
            net_income = extract_latest_value(facts, "NetIncomeLoss", "10-K")
            if net_income:
                findings.append(
                    AdapterFinding(
                        key="edgar_net_income_annual",
                        value=str(net_income["value"]),
                        status="confirmed",
                        adapter="edgar_filings",
                        observed_at=now,
                        snippet=f"Annual net income: ${net_income['value']:,} ({net_income['end_date']})",
                        citations=[
                            Citation(
                                source="SEC EDGAR XBRL Company Facts",
                                url=f"{SEC_API_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
                                query=f"CIK:{cik}, Concept:NetIncomeLoss",
                                accessed_at=now,
                            )
                        ],
                    )
                )

        print(f"[EDGAR] Found {len(findings)} findings for {company} (CIK: {cik})")

    except Exception as e:
        print(f"[EDGAR] Error checking filings: {e}")
        findings.append(
            AdapterFinding(
                key="edgar_error",
                value=str(e),
                status="error",
                adapter="edgar_filings",
                observed_at=now,
                snippet=f"Error accessing SEC EDGAR: {e}",
                citations=[
                    Citation(
                        source="SEC EDGAR API",
                        url=SEC_API_BASE,
                        query=f"company:{company}",
                        accessed_at=now,
                    )
                ],
            )
        )

    return findings
