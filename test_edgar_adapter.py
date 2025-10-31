"""
Quick test script for the enhanced EDGAR adapter.

Tests CIK lookup and filing fetching with real companies.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from iva.adapters.edgar_filings import (
    lookup_cik,
    get_company_submissions,
    get_company_facts,
    extract_latest_value,
    check_edgar_filings
)


async def test_cik_lookup():
    """Test CIK lookup by ticker and company name"""
    print("\n=== Testing CIK Lookup ===\n")
    
    # Test with ticker
    cik = await lookup_cik(ticker="AAPL")
    print(f"Apple (AAPL) CIK: {cik}")
    assert cik == "0000320193", f"Expected Apple CIK 0000320193, got {cik}"
    
    # Test with company name
    cik = await lookup_cik(company_name="Microsoft Corporation")
    print(f"Microsoft CIK: {cik}")
    assert cik == "0000789019", f"Expected Microsoft CIK 0000789019, got {cik}"
    
    # Test with Tesla
    cik = await lookup_cik(ticker="TSLA")
    print(f"Tesla (TSLA) CIK: {cik}")
    assert cik == "0001318605", f"Expected Tesla CIK 0001318605, got {cik}"
    
    # Test with non-existent company
    cik = await lookup_cik(company_name="Fake Company XYZ")
    print(f"Fake Company CIK: {cik}")
    assert cik is None, f"Expected None for fake company, got {cik}"
    
    print("\n✅ CIK lookup tests passed!\n")


async def test_company_submissions():
    """Test fetching company submissions"""
    print("\n=== Testing Company Submissions ===\n")
    
    cik = "0000320193"  # Apple
    data = await get_company_submissions(cik)
    
    assert data is not None, "Failed to fetch submissions"
    assert data["name"] == "Apple Inc.", f"Expected 'Apple Inc.', got {data['name']}"
    assert "AAPL" in data["tickers"], f"Expected AAPL in tickers, got {data['tickers']}"
    
    print(f"Company: {data['name']}")
    print(f"Tickers: {data['tickers']}")
    print(f"Exchanges: {data['exchanges']}")
    print(f"Recent filings count: {len(data['filings']['recent']['form'])}")
    
    print("\n✅ Company submissions test passed!\n")


async def test_company_facts():
    """Test fetching XBRL financial data"""
    print("\n=== Testing Company Facts (XBRL) ===\n")
    
    cik = "0000320193"  # Apple
    facts = await get_company_facts(cik)
    
    assert facts is not None, "Failed to fetch facts"
    
    # Extract revenue
    revenue = extract_latest_value(facts, "RevenueFromContractWithCustomerExcludingAssessedTax", "10-K")
    
    if revenue:
        print(f"Latest Annual Revenue: ${revenue['value']:,}")
        print(f"Period End: {revenue['end_date']}")
        print(f"Filed: {revenue['filed_date']}")
        print(f"Fiscal Year: {revenue['fy']}")
        assert revenue['value'] > 0, "Revenue should be positive"
    
    # Extract assets
    assets = extract_latest_value(facts, "Assets", "10-K")
    
    if assets:
        print(f"\nTotal Assets: ${assets['value']:,}")
        print(f"Period End: {assets['end_date']}")
        assert assets['value'] > 0, "Assets should be positive"
    
    print("\n✅ Company facts test passed!\n")


async def test_full_adapter():
    """Test the complete adapter with real companies"""
    print("\n=== Testing Full EDGAR Adapter ===\n")
    
    # Test with Apple (has ticker)
    print("Testing Apple Inc. (AAPL)...\n")
    findings = await check_edgar_filings("Apple Inc.", ticker="AAPL")
    
    print(f"Found {len(findings)} findings:")
    for finding in findings:
        print(f"  - {finding.key}: {finding.value} ({finding.status})")
        if finding.snippet:
            print(f"    {finding.snippet[:100]}...")
    
    assert len(findings) > 0, "Should have at least one finding"
    
    # Verify we got key data points
    finding_keys = [f.key for f in findings]
    assert "edgar_company_name" in finding_keys, "Should have company name"
    
    print("\n✅ Full adapter test passed!\n")


async def test_private_company():
    """Test with a private company (should return not found)"""
    print("\n=== Testing Private Company (Stripe) ===\n")
    
    findings = await check_edgar_filings("Stripe Inc.", ticker=None)
    
    print(f"Found {len(findings)} findings:")
    for finding in findings:
        print(f"  - {finding.key}: {finding.value} ({finding.status})")
    
    # Should have a "not found" finding
    assert any(f.key == "edgar_cik" and f.status == "not_found" for f in findings), \
        "Should indicate CIK not found for private company"
    
    print("\n✅ Private company test passed!\n")


async def main():
    """Run all tests"""
    print("="*60)
    print("EDGAR ADAPTER TEST SUITE")
    print("="*60)
    
    try:
        await test_cik_lookup()
        await test_company_submissions()
        await test_company_facts()
        await test_full_adapter()
        await test_private_company()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
