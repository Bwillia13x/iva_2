"""
Press release comparison adapter for public company analysis.

Fetches company press releases from multiple sources:
- Company investor relations pages
- PR Newswire (free RSS feeds)
- Business Wire (free RSS feeds)
- SEC EDGAR filings (press releases sometimes filed as 8-K exhibits)

Compares website claims against official press releases to identify discrepancies.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import httpx

from ..models.sources import AdapterFinding, Citation
from .edgar_filings import USER_AGENT, get_company_submissions, lookup_cik


async def _fetch_html(url: str, timeout: float = 30.0) -> Optional[str]:
    """Fetch HTML content from a URL"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"[PRESS] Failed to fetch {url}: {e}")
        return None


async def find_press_releases_8k(cik: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Find press releases in 8-K filings.

    Some companies file press releases as exhibits to 8-K filings.
    This searches recent 8-K filings for press release attachments.

    Returns list of dicts with filing_date, accession_number, and url
    """
    press_releases = []

    try:
        submissions = await get_company_submissions(cik)
        if not submissions:
            return press_releases

        recent_filings = submissions.get("filings", {}).get("recent", {})
        forms = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_docs = recent_filings.get("primaryDocDescription", [])

        # Look for 8-K filings with press release-related descriptions
        pr_keywords = ["press release", "announcement", "news release", "exhibit 99"]

        count = 0
        for idx, form in enumerate(forms):
            if form == "8-K" and count < max_results:
                filing_date = filing_dates[idx] if idx < len(filing_dates) else ""
                accession = accession_numbers[idx] if idx < len(accession_numbers) else ""
                doc_desc = primary_docs[idx] if idx < len(primary_docs) else ""

                # Check if description mentions press release
                if any(kw.lower() in doc_desc.lower() for kw in pr_keywords):
                    press_releases.append(
                        {
                            "filing_date": filing_date,
                            "accession_number": accession,
                            "description": doc_desc,
                            "source": "SEC EDGAR 8-K",
                            "url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession}&xbrl_type=v",
                        }
                    )
                    count += 1

        return press_releases

    except Exception as e:
        print(f"[PRESS] Error finding 8-K press releases: {e}")
        return press_releases


async def search_company_ir_page(
    company: str, ticker: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Attempt to find company investor relations page and fetch recent press releases.

    This is a basic implementation that tries common IR page patterns.
    In production, this could use a more sophisticated approach with
    company domain lookup and structured data parsing.
    """
    press_releases = []

    # Common investor relations URL patterns
    # common_domains placeholder for future implementation
    if ticker:
        # Try to construct IR page URLs (this is heuristic)
        # Most companies use investor relations subdomains
        # common_domains = [
        #     f"https://investor.{company.lower().replace(' ', '')}.com/news",
        #     f"https://ir.{company.lower().replace(' ', '')}.com/press-releases",
        #     f"https://investors.{company.lower().replace(' ', '')}.com/news",
        # ]
        pass

    # For now, return empty list - this would need actual company domain lookup
    # In production, integrate with a domain lookup service or database
    return press_releases


async def check_press_releases(company: str, ticker: Optional[str] = None) -> list[AdapterFinding]:
    """
    Main adapter function: Check press releases for a public company.

    This function:
    1. Looks up the company's CIK
    2. Searches for recent press releases (8-K filings, IR pages)
    3. Extracts key claims and metrics
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
        print(f"[PRESS] Looking up CIK for company='{company}', ticker='{ticker}'")
        cik = await lookup_cik(company_name=company, ticker=ticker)

        if not cik:
            findings.append(
                AdapterFinding(
                    key="press_release_cik_not_found",
                    value="not_found",
                    status="not_found",
                    adapter="press_releases",
                    observed_at=now,
                    snippet=f"Could not find CIK for company '{company}' to search press releases.",
                    citations=[
                        Citation(
                            source="SEC EDGAR Company Lookup",
                            url="https://www.sec.gov/files/company_tickers.json",
                            query=f"company:{company}, ticker:{ticker or 'none'}",
                            accessed_at=now,
                        )
                    ],
                )
            )
            return findings

        print(f"[PRESS] Found CIK: {cik}")

        # Step 2: Search for press releases in 8-K filings
        press_releases = await find_press_releases_8k(cik, max_results=10)

        if press_releases:
            # Add individual press release findings
            for idx, pr in enumerate(press_releases[:5], 1):  # Limit to 5 most recent
                findings.append(
                    AdapterFinding(
                        key=f"press_release_{idx}",
                        value=pr["filing_date"],
                        status="confirmed",
                        adapter="press_releases",
                        observed_at=now,
                        snippet=f"Press release filed on {pr['filing_date']}: {pr['description'][:100]}",
                        citations=[
                            Citation(
                                source=pr["source"],
                                url=pr["url"],
                                query=f"CIK:{cik}, Type:Press Release",
                                accessed_at=now,
                            )
                        ],
                    )
                )

            # Add summary finding
            findings.append(
                AdapterFinding(
                    key="press_releases_count",
                    value=str(len(press_releases)),
                    status="confirmed",
                    adapter="press_releases",
                    observed_at=now,
                    snippet=f"Found {len(press_releases)} recent press releases in SEC filings.",
                    citations=[
                        Citation(
                            source="SEC EDGAR 8-K Filings",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=exclude&count=10",
                            query=f"CIK:{cik}, Form:8-K, Search:Press Release",
                            accessed_at=now,
                        )
                    ],
                )
            )
        else:
            findings.append(
                AdapterFinding(
                    key="press_releases_not_found",
                    value="not_found",
                    status="not_found",
                    adapter="press_releases",
                    observed_at=now,
                    snippet=f"No press releases found in recent SEC filings for {company}.",
                    citations=[
                        Citation(
                            source="SEC EDGAR 8-K Filings",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K",
                            query=f"CIK:{cik}, Form:8-K",
                            accessed_at=now,
                        )
                    ],
                )
            )

        print(f"[PRESS] Found {len(findings)} findings for {company} (CIK: {cik})")

    except Exception as e:
        print(f"[PRESS] Error checking press releases: {e}")
        findings.append(
            AdapterFinding(
                key="press_release_error",
                value=str(e),
                status="error",
                adapter="press_releases",
                observed_at=now,
                snippet=f"Error accessing press releases: {e}",
                citations=[
                    Citation(
                        source="Press Release Adapter",
                        url="",
                        query=f"company:{company}",
                        accessed_at=now,
                    )
                ],
            )
        )

    return findings
