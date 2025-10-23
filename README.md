# Iva 2.0 Reality Layer – AI-Powered Fintech Truth Meter

> **An AI-native venture capital analyst that automatically screens fintech companies by verifying their claims against authoritative regulatory sources.**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Available-success)](https://replit.com/@username/iva-reality-layer)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5-412991.svg)](https://openai.com)

---

## 🎯 What It Does

Iva transforms fintech due diligence from a manual, time-consuming process into an automated, AI-powered workflow:

1. **📥 Ingest** – Scrapes company websites (with JavaScript rendering support)
2. **🔍 Extract** – Uses GPT-5codex to identify licensing, partner-bank, and compliance claims
3. **✅ Verify** – Queries authoritative sources (NMLS, FINTRAC, EDGAR, CFPB, bank partner lists)
4. **⚖️ Reconcile** – AI reasoning (chatgpt5thinking) identifies discrepancies with severity ratings
5. **📊 Report** – Generates truth cards and detailed HTML memos

**Result**: High-confidence, severity-rated truth cards that flag potential red flags in seconds, not days.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Interface (FastAPI)                │
│          Form Input → Live Results → Export Reports          │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │      Iva Core Engine              │
        │  (Claim Extraction & Reconciliation) │
        └──────┬──────────────────┬──────────┘
               │                  │
    ┌──────────▼─────────┐   ┌───▼────────────────┐
    │  LLM Orchestration │   │  Adapter Layer     │
    │                    │   │                    │
    │  • GPT-5codex      │   │  • NMLS Consumer   │
    │  • chatgpt5thinking│   │  • SEC EDGAR       │
    │  • Structured      │   │  • CFPB Database   │
    │    Extraction      │   │  • FINTRAC         │
    │  • Reasoning       │   │  • Bank Partners   │
    └────────────────────┘   │  • News Sources    │
                             └────────────────────┘
```

### Tech Stack

**Backend**: FastAPI (Python 3.11+) with async/await  
**AI/LLM**: OpenAI API (GPT-5codex for extraction, chatgpt5thinking for reasoning)  
**Web Scraping**: Playwright (JS rendering), BeautifulSoup4, Trafilatura  
**Templating**: Jinja2 for dynamic HTML reports  
**Optional**: PostgreSQL + pgvector, Neo4j (disabled by default)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd iva-reality-layer

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Web Server

```bash
# Development server
python -m uvicorn src.iva.server:app --host 0.0.0.0 --port 5000 --reload

# Or use make
make run
```

Visit `http://localhost:5000` in your browser.

### CLI Usage

```bash
python -m src.iva.cli verify \
  --url "https://acmefintech.com" \
  --company "Acme Payments Inc." \
  --jurisdiction US
```

---

## 💡 Key Features

### 🎨 **Clean Web Interface**
- Simple form-based UI for entering company details
- Real-time analysis with progress feedback
- Copy-to-clipboard for JSON and HTML reports

### 🤖 **AI-Powered Extraction**
- GPT-5codex extracts structured claims (licensing, partnerships, security)
- Handles complex, unstructured website content
- Supports JavaScript-rendered SPAs

### 🔎 **Multi-Source Verification**
- **NMLS Consumer Access** – Money transmitter licenses
- **SEC EDGAR** – Public company filings
- **CFPB Database** – Consumer complaints and enforcement actions
- **FINTRAC** – Canadian money services businesses
- **Bank Partner Pages** – Sponsor bank relationships
- **News Sources** – Recent regulatory actions

### ⚡ **Intelligent Reconciliation**
- AI reasoning identifies mismatches between claims and evidence
- Severity ratings: **High** 🛑 | **Medium** ⚠️ | **Low** ℹ️
- Confidence scores for each finding
- Detailed "why it matters" explanations

### 📄 **Professional Reporting**
- **Truth Cards**: Summary view with severity breakdown
- **HTML Memos**: Detailed, shareable reports
- **JSON Export**: Structured data for further analysis

---

## 📂 Project Structure

```
src/iva/
├── adapters/          # External data source integrations
│   ├── nmls.py        # NMLS Consumer Access
│   ├── edgar.py       # SEC EDGAR filings
│   ├── cfpb.py        # CFPB enforcement database
│   ├── fintrac.py     # Canadian regulator
│   ├── bank_partners.py  # Sponsor bank verification
│   └── news.py        # News and regulatory alerts
│
├── ingestion/         # Web scraping and content extraction
│   ├── fetch.py       # HTTP + Playwright fetching
│   ├── parse.py       # HTML parsing and cleaning
│   └── normalize.py   # Content normalization
│
├── llm/               # LLM orchestration
│   ├── client.py      # OpenAI API calls (json_call, text_call)
│   └── prompts/       # System prompts for extraction
│
├── models/            # Pydantic data models
│   ├── claims.py      # ClaimSet, ExtractedClaim
│   ├── sources.py     # AdapterFinding, Citation
│   └── recon.py       # TruthCard, Discrepancy
│
├── reconcile/         # Claim reconciliation engine
│   ├── engine.py      # Core reconciliation logic
│   ├── severity.py    # Severity classification
│   └── citations.py   # Source citation management
│
├── notify/            # Output and notifications
│   ├── memo.py        # HTML report generation
│   └── slack.py       # Slack webhook integration
│
├── web/templates/     # Jinja2 templates for web UI
│   ├── base.html      # Layout template
│   └── index.html     # Main interface
│
├── eval/              # Evaluation and testing
│   ├── harness.py     # Test harness
│   ├── metrics.py     # Performance metrics
│   └── datasets/      # Golden datasets
│
├── cli.py             # Command-line interface
├── config.py          # Configuration and settings
├── server.py          # FastAPI web server
└── logging.py         # Structured logging
```

---

## 🧪 Testing

```bash
# Run unit and end-to-end tests
pytest

# Or use make
make test

# Code quality checks
make lint    # ruff check
make format  # ruff format
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `OPENAI_MODEL_CODE` | ❌ | `gpt-5codex` | Model for structured extraction |
| `OPENAI_MODEL_REASONING` | ❌ | `chatgpt5thinking` | Model for reasoning tasks |
| `SLACK_WEBHOOK_URL` | ❌ | - | Slack webhook for notifications |
| `USE_POSTGRES` | ❌ | `false` | Enable PostgreSQL storage |
| `USE_PGVECTOR` | ❌ | `false` | Enable vector search |
| `USE_NEO4J` | ❌ | `false` | Enable graph database |

---

## 🎓 Use Cases

### For Venture Capital Firms
- **Deal Screening**: Quickly validate fintech startup claims before first call
- **Due Diligence**: Automated compliance and licensing verification
- **Portfolio Monitoring**: Regular re-verification of portfolio company claims

### For Regulatory Compliance
- **Audit Preparation**: Document claim verification with full citations
- **Risk Assessment**: Identify high-severity discrepancies early
- **Regulatory Mapping**: Cross-reference claims against multiple jurisdictions

### For Competitive Intelligence
- **Market Analysis**: Compare competitor claims at scale
- **Trend Identification**: Track regulatory changes affecting fintech

---

## ⚠️ Important Notes

- **Advisory Only**: Outputs are advisory and not legal advice
- **Respect robots.txt**: Scraper respects website policies
- **API Costs**: OpenAI API calls incur costs based on usage
- **Prototype Stage**: Some adapters use stubbed data (marked as "MVP stub")

---

## 🚧 Roadmap

- [ ] **Real-time adapters**: Replace stubs with live API integrations
- [ ] **Multi-jurisdiction**: Expand beyond US/CA to EU, UK, APAC
- [ ] **Historical tracking**: Store and compare analyses over time
- [ ] **Batch processing**: Analyze multiple companies in parallel
- [ ] **PDF Export**: Professional PDF reports
- [ ] **API endpoint**: RESTful API for programmatic access
- [ ] **Dashboard**: Analytics and insights visualization

---

## 📝 License

This project is provided as-is for demonstration and educational purposes.

---

## 🤝 Contributing

This is a personal project. For questions or collaboration, please reach out directly.

---

**Built with ❤️ for the future of intelligent due diligence**
