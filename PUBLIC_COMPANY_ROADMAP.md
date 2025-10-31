# Public Company Analysis - Implementation Roadmap

## Overview
Extending Iva's Reality Layer to analyze publicly traded companies by verifying claims against SEC filings and other authoritative sources.

## Phase 1: Core Infrastructure ✅ COMPLETED
**Timeline**: 2-3 weeks  
**Started**: October 31, 2025  
**Completed**: October 31, 2025

### Objectives
- [x] Project planning and roadmap creation
- [x] Enhance EDGAR adapter with comprehensive filing parsing
- [x] Add CIK lookup functionality (ticker → CIK mapping)
- [x] Add XBRL financial data parsing
- [x] Update data models for public company claims
- [x] Add public company UI toggle and ticker input
- [x] Integrate EDGAR adapter into CLI and server
- [ ] Create section extraction for 10-K/10-Q filings (moved to Phase 2)
- [ ] Add reconciliation rules for new claim types (moved to Phase 2)

### Technical Components

#### 1. Enhanced EDGAR Adapter ✅
**File**: `src/iva/adapters/edgar_filings.py`
- [x] CIK lookup from company name/ticker
- [x] Fetch company submissions via SEC API
- [x] Parse 10-K annual reports (basic metadata)
- [x] XBRL financial data extraction (revenue, assets, net income)
- [x] Proper rate limiting (10 req/sec SEC limit)
- [x] Error handling and retry logic
- [ ] Parse 10-Q quarterly reports (deferred to Phase 2)
- [ ] Parse 8-K material event filings (deferred to Phase 2)
- [ ] Extract specific sections (Item 3 Legal, Item 1A Risk, Item 7 MD&A) (deferred to Phase 2)

#### 2. Data Models ✅
**File**: `src/iva/models/claims.py`
- [x] Add new claim categories:
  - `financial_performance` - Revenue, profit, growth claims
  - `market_position` - Market leadership, rankings
  - `business_metrics` - User counts, transactions, retention
  - `forward_looking` - Guidance, projections
  - `governance` - Board, ESG claims
  - `litigation` - Lawsuit exposure
  - `intellectual_property` - Patent claims
  - `material_events` - M&A, partnerships
- [x] Updated CLAIMS_SCHEMA in CLI to include all 14 categories

#### 3. Reconciliation Rules (Phase 2)
**File**: `src/iva/reconcile/engine.py`
- [ ] Financial performance claim validation (deferred to Phase 2)
- [ ] Market position claim verification (deferred to Phase 2)
- [ ] Forward-looking statement compliance checks (deferred to Phase 2)
- [ ] Litigation disclosure reconciliation (deferred to Phase 2)

#### 4. UI Enhancement ✅
**File**: `src/iva/web/templates/index.html`
- [x] Add ticker symbol input field (optional)
- [x] Add public company demo buttons (Apple, PayPal, Marqeta)
- [x] Separate demo sections for Private vs Public companies
- [x] Modern gradient design with improved visual hierarchy
- [x] Server integration (ticker parameter passed through)

#### 5. Testing
- [x] Basic unit tests for EDGAR adapter (test_edgar_adapter.py)
- [x] Manual testing with Apple, Microsoft, Tesla
- [ ] End-to-end integration tests with live website analysis (recommended next step)
- [ ] Full validation of claim extraction and reconciliation

### Data Sources (Free Tier)
- ✅ SEC EDGAR REST API (`data.sec.gov`)
- ✅ SEC Submissions API
- ✅ SEC Company Facts API (XBRL)
- ✅ SEC Full-Text Search

### Success Metrics
- [x] Can successfully look up any public company by ticker
- [x] Can extract XBRL financial data from SEC API
- [x] UI supports ticker input and public company demos
- [x] CLI supports --ticker parameter for public company analysis
- [x] CLAIMS_SCHEMA includes all 14 claim categories (6 legacy + 8 new)
- [ ] Can reconcile website claims against SEC filings (needs testing)
- [ ] Analysis completes in <90 seconds for public companies (needs benchmarking)

---

## Phase 2: New Claim Categories
**Timeline**: 2 weeks  
**Status**: 🔜 NOT STARTED

### Objectives
- Extend claim extraction prompts for financial/governance claims
- Update reconciliation engine with new validation rules
- Add financial claim validation logic
- Test against real-world company websites

---

## Phase 3: Enhanced Sources
**Timeline**: 3 weeks  
**Status**: 🔜 NOT STARTED

### Objectives
- Integrate earnings call transcript analysis
- Add press release comparison adapter
- Implement analyst coverage checks
- Add historical claim tracking

---

## Phase 4: Advanced Features
**Timeline**: 3-4 weeks  
**Status**: 🔜 NOT STARTED

### Objectives
- Historical tracking (claim changes over time)
- Peer comparison (industry benchmarking)
- Automated alerts for material changes
- Public API for programmatic access
- Export to PDF reports

---

## Notes & Decisions

### Architecture Decisions
- **Free SEC API**: Using official `data.sec.gov` API (free, no auth required)
- **Rate Limiting**: 10 requests/second maximum per SEC requirements
- **User-Agent**: Must include contact email in all SEC API requests
- **Caching**: Will cache SEC responses to minimize API calls

### Key Constraints
- SEC API requires User-Agent header with contact info
- Must respect 10 req/sec rate limit
- XBRL data can be complex - may need multiple parsing strategies
- Some filings are HTML, some are XBRL, some are PDF

### Open Questions
- [ ] Should we cache SEC filings locally or fetch fresh each time?
- [ ] How far back in filing history should we look?
- [ ] Should we support international stock exchanges (LSE, TSX, etc.)?
- [ ] What's the UX for companies with multiple tickers?

---

## Progress Log

### October 31, 2025
- ✅ Created implementation roadmap
- ✅ Researched SEC EDGAR API capabilities
- ✅ Identified free data sources
- ✅ Defined Phase 1 scope and objectives
- ✅ Implemented enhanced EDGAR adapter with CIK lookup and XBRL parsing
- ✅ Extended claim models from 6 to 14 categories
- ✅ Integrated public company support in UI, server, and CLI
- ✅ Passed code review - critical blockers resolved
- 🎉 **Phase 1 Complete** - Ready for end-to-end testing

---

## Resources

### Documentation
- [SEC EDGAR API Official Docs](https://www.sec.gov/edgar/sec-api-documentation)
- [SEC API Overview PDF](https://www.sec.gov/files/edgar/filer-information/api-overview.pdf)
- [Company Facts API](https://data.sec.gov/api/xbrl/)

### Example API Endpoints
```
# Get company submissions
https://data.sec.gov/submissions/CIK0000320193.json

# Get all financial facts (XBRL)
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

# Get specific metric
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json
```

### Sample Companies for Testing
- Apple Inc. (AAPL) - CIK: 0000320193
- Microsoft (MSFT) - CIK: 0000789019
- Tesla (TSLA) - CIK: 0001318605
- Stripe (private for comparison)
