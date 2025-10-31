"""
Historical claim tracking for public company analysis.

Tracks claim changes over time by storing historical claim sets and comparing
current claims against previous versions to identify changes, inconsistencies, and trends.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.claims import ClaimSet, ExtractedClaim
from ..models.sources import AdapterFinding, Citation

# Store historical claims in data directory
HISTORICAL_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "historical"
HISTORICAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_company_history_file(company: str) -> Path:
    """Get the file path for storing a company's historical claims"""
    # Normalize company name for filename
    safe_name = (
        "".join(c for c in company if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
    )
    return HISTORICAL_DATA_DIR / f"{safe_name}_claims.jsonl"


def save_claim_set(claim_set: ClaimSet) -> None:
    """
    Save a claim set to historical tracking.

    Stores claims as JSONL (one JSON object per line) for easy appending.
    """
    history_file = _get_company_history_file(claim_set.company)

    # Convert claim set to dict
    record = {
        "url": claim_set.url,
        "company": claim_set.company,
        "extracted_at": claim_set.extracted_at.isoformat(),
        "claims": [
            {
                "id": c.id,
                "category": c.category,
                "claim_text": c.claim_text,
                "entity": c.entity,
                "jurisdiction": c.jurisdiction,
                "claim_kind": c.claim_kind,
                "values": c.values,
                "effective_date": c.effective_date,
                "confidence": c.confidence,
            }
            for c in claim_set.claims
        ],
    }

    # Append to history file
    try:
        with open(history_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[HISTORICAL] Error saving claim set for {claim_set.company}: {e}")


def load_historical_claims(company: str, limit: int = 10) -> List[ClaimSet]:
    """
    Load historical claim sets for a company.

    Returns the most recent N claim sets.
    """
    history_file = _get_company_history_file(company)

    if not history_file.exists():
        return []

    records = []
    with open(history_file, "r") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Sort by extracted_at descending and limit
    records.sort(key=lambda x: x.get("extracted_at", ""), reverse=True)
    records = records[:limit]

    # Convert back to ClaimSet objects
    claim_sets = []
    for record in records:
        claims = [
            ExtractedClaim(
                id=c.get("id", ""),
                category=c["category"],
                claim_text=c["claim_text"],
                entity=c.get("entity"),
                jurisdiction=c.get("jurisdiction"),
                claim_kind=c.get("claim_kind"),
                values=c.get("values"),
                effective_date=c.get("effective_date"),
                confidence=c.get("confidence", 0.6),
                citations=[],
            )
            for c in record.get("claims", [])
        ]
        claim_sets.append(
            ClaimSet(
                url=record["url"],
                company=record["company"],
                extracted_at=datetime.fromisoformat(record["extracted_at"]),
                claims=claims,
            )
        )

    return claim_sets


def compare_claims(current: ClaimSet, previous: ClaimSet) -> Dict[str, Any]:
    """
    Compare current claims against previous claims to identify changes.

    Returns dict with:
    - new_claims: Claims in current but not in previous
    - removed_claims: Claims in previous but not in current
    - modified_claims: Claims that exist in both but have changed
    - unchanged_claims: Claims that are identical
    """
    # Create indexes by claim text (simplified comparison)
    current_by_text = {c.claim_text: c for c in current.claims}
    previous_by_text = {c.claim_text: c for c in previous.claims}

    new_claims = [c for text, c in current_by_text.items() if text not in previous_by_text]
    removed_claims = [c for text, c in previous_by_text.items() if text not in current_by_text]

    # Check for modified claims (same text but different values/details)
    modified_claims = []
    unchanged_claims = []

    for text, current_claim in current_by_text.items():
        if text in previous_by_text:
            prev_claim = previous_by_text[text]
            # Compare key fields
            if (
                current_claim.values != prev_claim.values
                or current_claim.category != prev_claim.category
                or current_claim.confidence != prev_claim.confidence
            ):
                modified_claims.append(
                    {
                        "current": current_claim,
                        "previous": prev_claim,
                    }
                )
            else:
                unchanged_claims.append(current_claim)

    return {
        "new_claims": new_claims,
        "removed_claims": removed_claims,
        "modified_claims": modified_claims,
        "unchanged_claims": unchanged_claims,
        "comparison_date": current.extracted_at.isoformat(),
        "previous_date": previous.extracted_at.isoformat(),
    }


async def get_claim_history_summary(company: str) -> List[AdapterFinding]:
    """
    Generate historical findings for a company based on claim history.

    Returns AdapterFinding objects that can be used in reconciliation.
    """
    findings: List[AdapterFinding] = []
    now = datetime.now(UTC)

    historical = load_historical_claims(company, limit=5)

    if len(historical) < 2:
        # Not enough history for comparison
        findings.append(
            AdapterFinding(
                key="historical_claims_insufficient",
                value="insufficient",
                status="not_found",
                adapter="historical_tracking",
                observed_at=now,
                snippet=f"Insufficient historical data for {company} (need at least 2 claim sets).",
                citations=[
                    Citation(
                        source="Historical Claim Tracking",
                        url=str(_get_company_history_file(company)),
                        query=f"company:{company}",
                        accessed_at=now,
                    )
                ],
            )
        )
        return findings

    # Compare most recent vs previous
    current = historical[0]
    previous = historical[1]

    comparison = compare_claims(current, previous)

    # Generate findings based on changes
    if comparison["new_claims"]:
        findings.append(
            AdapterFinding(
                key="historical_new_claims",
                value=str(len(comparison["new_claims"])),
                status="confirmed",
                adapter="historical_tracking",
                observed_at=now,
                snippet=f"Found {len(comparison['new_claims'])} new claim(s) compared to previous extraction ({previous.extracted_at.date()}).",
                citations=[
                    Citation(
                        source="Historical Claim Tracking",
                        url=str(_get_company_history_file(company)),
                        query=f"company:{company}, comparison:new_claims",
                        accessed_at=now,
                    )
                ],
            )
        )

    if comparison["removed_claims"]:
        findings.append(
            AdapterFinding(
                key="historical_removed_claims",
                value=str(len(comparison["removed_claims"])),
                status="confirmed",
                adapter="historical_tracking",
                observed_at=now,
                snippet=f"Found {len(comparison['removed_claims'])} removed claim(s) compared to previous extraction ({previous.extracted_at.date()}).",
                citations=[
                    Citation(
                        source="Historical Claim Tracking",
                        url=str(_get_company_history_file(company)),
                        query=f"company:{company}, comparison:removed_claims",
                        accessed_at=now,
                    )
                ],
            )
        )

    if comparison["modified_claims"]:
        findings.append(
            AdapterFinding(
                key="historical_modified_claims",
                value=str(len(comparison["modified_claims"])),
                status="confirmed",
                adapter="historical_tracking",
                observed_at=now,
                snippet=f"Found {len(comparison['modified_claims'])} modified claim(s) compared to previous extraction ({previous.extracted_at.date()}).",
                citations=[
                    Citation(
                        source="Historical Claim Tracking",
                        url=str(_get_company_history_file(company)),
                        query=f"company:{company}, comparison:modified_claims",
                        accessed_at=now,
                    )
                ],
            )
        )

    # Add summary finding
    total_changes = (
        len(comparison["new_claims"])
        + len(comparison["removed_claims"])
        + len(comparison["modified_claims"])
    )

    findings.append(
        AdapterFinding(
            key="historical_claims_status",
            value="has_history" if total_changes > 0 else "no_changes",
            status="confirmed",
            adapter="historical_tracking",
            observed_at=now,
            snippet=f"Historical tracking: {total_changes} total change(s) detected across {len(historical)} claim set(s).",
            citations=[
                Citation(
                    source="Historical Claim Tracking",
                    url=str(_get_company_history_file(company)),
                    query=f"company:{company}",
                    accessed_at=now,
                )
            ],
        )
    )

    return findings
