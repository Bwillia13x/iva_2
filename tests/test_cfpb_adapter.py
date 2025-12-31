"""
Test script for the real CFPB adapter.
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "src")

from iva.adapters.cfpb import check_cfpb

async def main():
    print("=" * 60)
    print("CFPB ADAPTER TEST")
    print("=" * 60)

    # Test with a company known to have complaints (e.g., Equifax, Wells Fargo, Coinbase)
    company = "Coinbase"
    print(f"\nTesting with company: {company}...")
    findings = await check_cfpb(company)

    print(f"Found {len(findings)} findings:")
    for f in findings:
        print(f"  - {f.key}: {f.value} ({f.status})")
        print(f"    Snippet: {f.snippet}")
        if f.citations:
            print(f"    URL: {f.citations[0].url}")

    assert any(f.key == "cfpb_complaints_found" and int(f.value) > 0 for f in findings), "Should find complaints for Coinbase"

    # Test with a likely clean/unknown company
    company = "NonExistentFintechXYZ123"
    print(f"\nTesting with company: {company}...")
    findings = await check_cfpb(company)

    print(f"Found {len(findings)} findings:")
    for f in findings:
        print(f"  - {f.key}: {f.value} ({f.status})")

    assert any(f.key == "cfpb_complaints_found" and f.value == "0" for f in findings), "Should find 0 complaints"

    print("\n" + "=" * 60)
    print("✅ CFPB TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
