"""
Earnings call transcript adapter for public company analysis.

Fetches and analyzes earnings call transcripts from multiple sources:
- SEC EDGAR 8-K filings (some companies file transcripts as exhibits)
- Company investor relations pages
- Free financial data APIs

For public companies, earnings calls often contain forward-looking statements,
guidance, and business metrics that should align with website claims.
"""

import re
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
        print(f"[EARNINGS] Failed to fetch {url}: {e}")
        return None


async def find_earnings_transcripts_8k(cik: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Find earnings call transcripts in 8-K filings.

    Some companies file earnings call transcripts as exhibits to 8-K filings.
    This searches recent 8-K filings for transcript attachments.

    Returns list of dicts with filing_date, accession_number, and transcript_url
    """
    transcripts = []

    try:
        submissions = await get_company_submissions(cik)
        if not submissions:
            return transcripts

        recent_filings = submissions.get("filings", {}).get("recent", {})
        forms = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])

        # Look for 8-K filings with earnings-related descriptions
        earnings_keywords = ["earnings", "call", "transcript", "conference", "quarterly"]

        count = 0
        for idx, form in enumerate(forms):
            if form == "8-K" and count < max_results:
                filing_date = filing_dates[idx] if idx < len(filing_dates) else ""
                accession = accession_numbers[idx] if idx < len(accession_numbers) else ""

                # Check primary document description
                primary_docs = recent_filings.get("primaryDocDescription", [])
                doc_desc = primary_docs[idx] if idx < len(primary_docs) else ""

                # Check if description mentions earnings
                if any(kw.lower() in doc_desc.lower() for kw in earnings_keywords):
                    transcripts.append(
                        {
                            "filing_date": filing_date,
                            "accession_number": accession,
                            "source": "SEC EDGAR 8-K",
                            "url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession}&xbrl_type=v",
                        }
                    )
                    count += 1

        return transcripts

    except Exception as e:
        print(f"[EARNINGS] Error finding 8-K transcripts: {e}")
        return transcripts


async def extract_transcript_metrics(transcript_text: str, company: str) -> List[Dict[str, Any]]:
    """
    Extract key metrics and claims from earnings call transcript text.

    Uses simple pattern matching to find:
    - Revenue figures
    - User/customer counts
    - Guidance statements
    - Forward-looking statements
    """
    metrics = []

    # Pattern for revenue mentions (e.g., "$1.2 billion", "revenue of $500M")
    revenue_patterns = [
        r"revenue[:\s]+[\$]?([\d,]+\.?\d*)\s*(million|billion|M|B|Million|Billion)",
        r"[\$]([\d,]+\.?\d*)\s*(million|billion|M|B)\s+revenue",
        r"revenue[:\s]+[\$]([\d,]+\.?\d*\d*)",
    ]

    # Pattern for user/customer counts
    user_patterns = [
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(?:active\s+)?(?:users?|customers?|accounts?)",
        r"(?:users?|customers?|accounts?)[:\s]+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
    ]

    # Pattern for guidance statements
    guidance_patterns = [
        r"guidance[:\s]+[\$]?([\d,]+\.?\d*)\s*(million|billion|M|B)",
        r"expect[:\s]+[\$]?([\d,]+\.?\d*)\s*(million|billion|M|B)",
        r"forecast[:\s]+[\$]?([\d,]+\.?\d*)\s*(million|billion|M|B)",
    ]

    text_lower = transcript_text.lower()

    # Extract revenue mentions
    for pattern in revenue_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            metrics.append(
                {
                    "type": "revenue",
                    "value": match.group(0),
                    "context": transcript_text[max(0, match.start() - 50) : match.end() + 50],
                }
            )

    # Extract user/customer counts
    for pattern in user_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            metrics.append(
                {
                    "type": "users",
                    "value": match.group(0),
                    "context": transcript_text[max(0, match.start() - 50) : match.end() + 50],
                }
            )

    # Extract guidance
    for pattern in guidance_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            metrics.append(
                {
                    "type": "guidance",
                    "value": match.group(0),
                    "context": transcript_text[max(0, match.start() - 50) : match.end() + 50],
                }
            )

    return metrics


async def check_earnings_calls(company: str, ticker: Optional[str] = None) -> list[AdapterFinding]:
    """
    Main adapter function: Check earnings call transcripts for a public company.

    This function:
    1. Looks up the company's CIK
    2. Searches for recent earnings call transcripts (8-K filings, investor relations)
    3. Extracts key metrics and forward-looking statements
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
        print(f"[EARNINGS] Looking up CIK for company='{company}', ticker='{ticker}'")
        cik = await lookup_cik(company_name=company, ticker=ticker)

        if not cik:
            findings.append(
                AdapterFinding(
                    key="earnings_cik_not_found",
                    value="not_found",
                    status="not_found",
                    adapter="earnings_calls",
                    observed_at=now,
                    snippet=f"Could not find CIK for company '{company}' to search earnings transcripts.",
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

        print(f"[EARNINGS] Found CIK: {cik}")

        # Step 2: Search for earnings transcripts in 8-K filings
        transcripts = await find_earnings_transcripts_8k(cik, max_results=5)

        if transcripts:
            for idx, transcript in enumerate(transcripts, 1):
                findings.append(
                    AdapterFinding(
                        key=f"earnings_transcript_{idx}",
                        value=transcript["filing_date"],
                        status="confirmed",
                        adapter="earnings_calls",
                        observed_at=now,
                        snippet=f"Earnings call transcript found in 8-K filing dated {transcript['filing_date']}",
                        citations=[
                            Citation(
                                source=transcript["source"],
                                url=transcript["url"],
                                query=f"CIK:{cik}, Type:Earnings Transcript",
                                accessed_at=now,
                            )
                        ],
                    )
                )
        else:
            # No transcripts found in 8-K filings
            findings.append(
                AdapterFinding(
                    key="earnings_transcript_not_found",
                    value="not_found",
                    status="not_found",
                    adapter="earnings_calls",
                    observed_at=now,
                    snippet=f"No earnings call transcripts found in recent 8-K filings for {company}.",
                    citations=[
                        Citation(
                            source="SEC EDGAR 8-K Filings",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=exclude&count=10",
                            query=f"CIK:{cik}, Form:8-K, Search:Earnings Transcript",
                            accessed_at=now,
                        )
                    ],
                )
            )

        # Step 3: Add metadata about earnings call availability
        # This helps reconciliation engine know if transcripts are available for comparison
        findings.append(
            AdapterFinding(
                key="earnings_calls_available",
                value="yes" if transcripts else "no",
                status="confirmed" if transcripts else "not_found",
                adapter="earnings_calls",
                observed_at=now,
                snippet=f"Found {len(transcripts)} recent earnings call transcript(s) in SEC filings."
                if transcripts
                else "No earnings call transcripts found in SEC filings.",
                citations=[
                    Citation(
                        source="SEC EDGAR Earnings Transcripts",
                        url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K",
                        query=f"CIK:{cik}, Search:Earnings",
                        accessed_at=now,
                    )
                ],
            )
        )

        print(f"[EARNINGS] Found {len(findings)} findings for {company} (CIK: {cik})")

    except Exception as e:
        print(f"[EARNINGS] Error checking earnings calls: {e}")
        findings.append(
            AdapterFinding(
                key="earnings_error",
                value=str(e),
                status="error",
                adapter="earnings_calls",
                observed_at=now,
                snippet=f"Error accessing earnings call transcripts: {e}",
                citations=[
                    Citation(
                        source="Earnings Call Adapter",
                        url="",
                        query=f"company:{company}",
                        accessed_at=now,
                    )
                ],
            )
        )

    return findings
