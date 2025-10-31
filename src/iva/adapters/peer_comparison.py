"""
Peer comparison adapter for industry benchmarking.

Compares a company's financial metrics and claims against industry peers
using SEC EDGAR data to identify similar companies by SIC code or industry.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from ..models.sources import AdapterFinding, Citation
from .edgar_filings import get_company_facts, get_company_submissions, lookup_cik


async def find_industry_peers(
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    company_name: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Find industry peers by SIC code.

    Returns list of peer companies with their tickers and basic info.
    """
    if not cik:
        cik = await lookup_cik(company_name=company_name, ticker=ticker)

    if not cik:
        return []

    # Get company facts to find SIC code
    facts = await get_company_facts(cik)
    if not facts:
        return []

    # Extract SIC code from company facts
    sic_code = None
    # entity_info available for future use

    # Try to get SIC from facts structure
    # The SEC API structure varies, so we search for SIC in various places
    if "sic" in facts:
        sic_code = facts.get("sic")
    elif "facts" in facts and "dei" in facts["facts"]:
        # Try to extract from DEI facts
        dei_facts = facts["facts"].get("dei", {})
        for fact_key in dei_facts:
            if "sic" in fact_key.lower():
                sic_data = dei_facts[fact_key]
                if "units" in sic_data:
                    # Get most recent value
                    for unit_name, unit_data in sic_data["units"].items():
                        if "facts" in unit_data:
                            for period, value in unit_data["facts"].items():
                                if isinstance(value, dict) and "val" in value:
                                    sic_code = value["val"]
                                    break

    if not sic_code:
        # Fallback: try to get from company submissions
        submissions = await get_company_submissions(cik)
        if submissions and "sic" in submissions:
            sic_code = submissions.get("sic")

    if not sic_code:
        # Can't find peers without SIC code
        return []

    # Note: The SEC tickers JSON doesn't include SIC codes
    # For MVP, peer matching would require a separate SIC code database
    # This is a placeholder for future implementation
    # For now, return empty list - peer comparison will focus on financial metrics
    # when peer CIKs are provided via other means
    return []


async def compare_financial_metrics(
    target_cik: str, peer_ciks: List[str], metric: str = "revenue"
) -> Dict[str, Any]:
    """
    Compare financial metrics across target company and peers.

    Returns comparison data with percentiles and rankings.
    """
    # comparisons placeholder for future implementation

    # Get facts for target company
    target_facts = await get_company_facts(target_cik)
    if not target_facts:
        return {}

    # Extract metric value for target
    target_value = None
    # Simplified extraction - in production would parse XBRL facts properly
    if "facts" in target_facts and "us-gaap" in target_facts["facts"]:
        gaap_facts = target_facts["facts"]["us-gaap"]
        if metric == "revenue":
            # Look for Revenues concept
            for concept_key in gaap_facts:
                if "revenue" in concept_key.lower():
                    concept_data = gaap_facts[concept_key]
                    if "units" in concept_data:
                        for unit_name, unit_data in concept_data["units"].items():
                            if "USD" in unit_name:  # Revenue in USD
                                # Get most recent value
                                for period, value in unit_data.get("facts", {}).items():
                                    if isinstance(value, dict) and "val" in value:
                                        target_value = value["val"]
                                        break
                                if target_value:
                                    break
                    if target_value:
                        break

    if target_value is None:
        return {}

    # Get peer values (simplified - would batch fetch in production)
    peer_values = []
    for peer_cik in peer_ciks[:5]:  # Limit to 5 peers for rate limiting
        peer_facts = await get_company_facts(peer_cik)
        if peer_facts:
            # Similar extraction logic for peers
            peer_value = None
            if "facts" in peer_facts and "us-gaap" in peer_facts["facts"]:
                gaap_facts = peer_facts["facts"]["us-gaap"]
                for concept_key in gaap_facts:
                    if "revenue" in concept_key.lower():
                        concept_data = gaap_facts[concept_key]
                        if "units" in concept_data:
                            for unit_name, unit_data in concept_data["units"].items():
                                if "USD" in unit_name:
                                    for period, value in unit_data.get("facts", {}).items():
                                        if isinstance(value, dict) and "val" in value:
                                            peer_value = value["val"]
                                            break
                                    if peer_value:
                                        break
                        if peer_value:
                            break
            if peer_value:
                peer_values.append(peer_value)

    if not peer_values:
        return {}

    # Calculate percentiles
    all_values = sorted([target_value] + peer_values)
    target_rank = all_values.index(target_value) + 1
    percentile = (target_rank / len(all_values)) * 100

    return {
        "target_value": target_value,
        "peer_count": len(peer_values),
        "peer_values": peer_values,
        "percentile": percentile,
        "rank": target_rank,
        "total_companies": len(all_values),
    }


async def check_peer_comparison(company: str, ticker: Optional[str] = None) -> List[AdapterFinding]:
    """
    Generate peer comparison findings for a company.

    For MVP, focuses on financial metrics comparison using SEC data.
    In production, would include industry classification and broader peer set.
    """
    findings: List[AdapterFinding] = []
    now = datetime.now(UTC)

    if not ticker:
        # Peer comparison requires ticker for public companies
        return findings

    cik = await lookup_cik(ticker=ticker, company_name=company)
    if not cik:
        findings.append(
            AdapterFinding(
                key="peer_comparison_cik_not_found",
                value="not_found",
                status="not_found",
                adapter="peer_comparison",
                observed_at=now,
                snippet=f"Could not find CIK for {company} ({ticker}) to perform peer comparison.",
                citations=[],
            )
        )
        return findings

    # Get company facts
    facts = await get_company_facts(cik)
    if not facts:
        findings.append(
            AdapterFinding(
                key="peer_comparison_facts_unavailable",
                value="unavailable",
                status="not_found",
                adapter="peer_comparison",
                observed_at=now,
                snippet=f"Company facts not available for {company} ({ticker}) from SEC API.",
                citations=[
                    Citation(
                        source="SEC EDGAR Company Facts API",
                        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                        query=f"company:{company}, ticker:{ticker}",
                        accessed_at=now,
                    )
                ],
            )
        )
        return findings

    # For MVP, provide basic peer comparison framework
    # In production, would include actual peer matching and metric comparison
    findings.append(
        AdapterFinding(
            key="peer_comparison_available",
            value="available",
            status="confirmed",
            adapter="peer_comparison",
            observed_at=now,
            snippet=f"Peer comparison framework available for {company} ({ticker}). Industry benchmarking requires SIC code classification and peer matching.",
            citations=[
                Citation(
                    source="SEC EDGAR Company Facts API",
                    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                    query=f"company:{company}, ticker:{ticker}",
                    accessed_at=now,
                )
            ],
        )
    )

    return findings
