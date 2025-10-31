# Public Company Analysis - Implementation Roadmap

## Overview
Extending Iva's Reality Layer to analyze publicly traded companies by verifying claims against SEC filings and other authoritative sources.

## Phase 1: Core Infrastructure ⏳ IN PROGRESS
**Timeline**: 2-3 weeks  
**Started**: October 31, 2025

### Objectives
- [x] Project planning and roadmap creation
- [ ] Enhance EDGAR adapter with comprehensive filing parsing
- [ ] Add CIK lookup functionality (ticker → CIK mapping)
- [ ] Create section extraction for 10-K/10-Q filings
- [ ] Add XBRL financial data parsing
- [ ] Update data models for public company claims
- [ ] Add public company UI toggle

### Technical Components

#### 1. Enhanced EDGAR Adapter
**File**: `src/iva/adapters/edgar_filings.py`
- [ ] CIK lookup from company name/ticker
- [ ] Fetch company submissions via SEC API
- [ ] Parse 10-K annual reports
- [ ] Parse 10-Q quarterly reports
- [ ] Parse 8-K material event filings
- [ ] Extract specific sections (Item 3 Legal, Item 1A Risk, Item 7 MD&A)
- [ ] XBRL financial data extraction
- [ ] Proper rate limiting (10 req/sec SEC limit)

#### 2. Data Models
**File**: `src/iva/models/claims.py`
- [ ] Add new claim categories:
  - `financial_performance` - Revenue, profit, growth claims
  - `market_position` - Market leadership, rankings
  - `business_metrics` - User counts, transactions, retention
  - `forward_looking` - Guidance, projections
  - `governance` - Board, ESG claims
  - `litigation` - Lawsuit exposure
  - `intellectual_property` - Patent claims
  - `material_events` - M&A, partnerships

#### 3. Reconciliation Rules
**File**: `src/iva/reconcile/engine.py`
- [ ] Financial performance claim validation
- [ ] Market position claim verification
- [ ] Forward-looking statement compliance checks
- [ ] Litigation disclosure reconciliation

#### 4. UI Enhancement
**File**: `src/iva/web/templates/index.html`
- [ ] Add company type selector (Private/Public)
- [ ] Add ticker symbol input field
- [ ] Add public company demo buttons
- [ ] Update form validation

#### 5. Testing
- [ ] Unit tests for EDGAR adapter
- [ ] Integration tests with live SEC API
- [ ] Test cases for major public companies (AAPL, MSFT, TSLA)

### Data Sources (Free Tier)
- ✅ SEC EDGAR REST API (`data.sec.gov`)
- ✅ SEC Submissions API
- ✅ SEC Company Facts API (XBRL)
- ✅ SEC Full-Text Search

### Success Metrics
- [ ] Can successfully look up any public company by ticker
- [ ] Can extract financial claims from 10-K/10-Q
- [ ] Can reconcile website claims against SEC filings
- [ ] Analysis completes in <90 seconds for public companies
- [ ] UI clearly distinguishes private vs. public company analysis

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
- 🏁 Ready to begin implementation

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
