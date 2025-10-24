# Iva 2.0 Reality Layer - Fintech Claim-to-Fact Truth Meter

## Overview
Iva's Reality Layer is a FastAPI web application that analyzes fintech company websites to verify their claims against authoritative sources. It extracts licensing, partner-bank, and security assertions from company websites, checks them against regulatory databases (NMLS, FINTRAC, EDGAR, CFPB), and produces a detailed truth card with severity ratings and confidence scores.

**Current State**: The application is fully configured and running on Replit. The web interface is accessible and ready to analyze company websites.

## Recent Changes

### October 24, 2025 - Analysis Quality & UX Improvements

**Phase 2: Output Quality Enhancements**
- **Added claim text to discrepancies**: Users now see WHAT is being flagged, not just WHY it matters
- **Enhanced HTML memo template**: Displays actual claims like "Join the millions of companies..." before verification details
- **Enabled JavaScript rendering**: All demo buttons now use JS rendering to extract more claims from modern websites
- **Improved actionability**: Output is now significantly more useful and understandable for non-technical users

**Phase 1: Core Analysis Improvements**
- **Fixed OpenAI Responses API integration**: Removed unsupported `response_format` parameter from Responses API calls
- **Enhanced claim extraction**: Completely rewrote prompt to extract 5 categories of claims (licensing, regulatory, partner_bank, security, compliance, marketing)
- **Expanded reconciliation engine**: Added 10+ new verification rules:
  - ISO/SOC 2/PCI certification validation
  - Marketing metric verification (customer counts, transaction volumes)
  - Vague marketing claim detection ("leading", "best", etc.)
  - Regulatory claim validation (SEC, CFPB)
  - Compliance program verification (AML/KYC, GDPR/CCPA)
- **Added comprehensive debug logging**: Full pipeline visibility from extraction through reconciliation
- **Improved output quality**: System now extracts 6+ claims and identifies 3+ discrepancies per analysis (vs 0/0 before)
- **Fixed jurisdiction enum**: Added proper validation for US/CA/EU/UK/OTHER values

### October 23, 2025 - Initial Setup
- Imported project from GitHub
- Installed Python 3.11 and all required dependencies
- Configured FastAPI server to run on port 5000 (Replit requirement)
- Set up workflow for automatic server restart
- Installed Playwright Chromium browser for web scraping
- Created .env file and configured OPENAI_API_KEY
- Added .gitignore for Python project
- Configured deployment settings for autoscale deployment
- Added python-multipart dependency for form handling

## Project Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Web Scraping**: Playwright, BeautifulSoup4, Trafilatura
- **AI/LLM**: OpenAI API (GPT models)
- **Templating**: Jinja2
- **Optional Databases**: PostgreSQL with pgvector, Neo4j (disabled by default)

### Directory Structure
```
src/iva/
├── adapters/       # External data source adapters (NMLS, EDGAR, CFPB, etc.)
├── eval/           # Evaluation harness and golden datasets
├── ingestion/      # Web scraping and content parsing
├── llm/            # LLM client and prompts
├── models/         # Data models (claims, events, sources)
├── notify/         # Slack notification integration
├── reconcile/      # Claim reconciliation engine
├── storage/        # Database and vector storage (optional)
├── web/templates/  # HTML templates for web interface
├── cli.py          # Command-line interface
├── config.py       # Configuration and settings
└── server.py       # FastAPI web server
```

### Key Features
1. **Web Interface**: Form-based UI to submit company URLs for analysis
2. **Claim Extraction**: Uses LLMs to extract verifiable claims from websites
3. **Source Verification**: Queries authoritative sources to verify claims
4. **Reconciliation**: Identifies discrepancies with severity ratings (high/med/low)
5. **Reporting**: Generates truth cards and HTML memos
6. **Optional Slack Integration**: Can post results to Slack channels

## Configuration

### Environment Variables
The application uses the following environment variables (configured in `.env`):

**Required:**
- `OPENAI_API_KEY` - OpenAI API key for LLM functionality (configured in Replit Secrets)

**Optional:**
- `OPENAI_MODEL_CODE` - Model for structured extraction tasks (default: gpt-5-codex)
- `OPENAI_MODEL_REASONING` - Model for reasoning tasks (default: gpt-5-thinking)
- `SLACK_WEBHOOK_URL` or `SLACK_BOT_TOKEN` + `SLACK_CHANNEL` - For Slack notifications
- `USE_POSTGRES`, `USE_PGVECTOR`, `USE_NEO4J` - Enable optional databases (all false by default)

### Running the Application
The FastAPI server runs automatically via the configured workflow:
- **Development**: Runs on http://0.0.0.0:5000 with auto-reload
- **Command**: `python -m uvicorn src.iva.server:app --host 0.0.0.0 --port 5000 --reload`

### CLI Usage
You can also run verification from the command line:
```bash
python -m src.iva.cli verify --url "https://example.com" --company "Example Inc." --jurisdiction US
```

## Development Notes

### Dependencies
All Python dependencies are managed via `requirements.txt` and installed automatically. Key dependencies include:
- FastAPI & Uvicorn for web server
- Playwright for JavaScript-rendered page scraping
- OpenAI SDK for LLM integration
- SQLAlchemy & AsyncPG for optional database support
- Beautiful Soup & Trafilatura for HTML parsing

### Testing
Run tests with: `pytest` or `make test`

### Code Quality
- Linting: `ruff check .`
- Formatting: `ruff format .`

## Deployment
The application is configured for autoscale deployment, which is ideal for this stateless web application. When you publish, it will:
- Run on port 5000
- Scale automatically based on traffic
- Use the production-ready uvicorn server (without --reload flag)

## Important Notes
- **Advisory Only**: Outputs are advisory and not legal advice
- **Respect robots.txt**: The scraper should respect website policies
- **API Costs**: OpenAI API calls will incur costs based on usage
- **Databases Optional**: PostgreSQL and Neo4j integrations are disabled by default and not required for basic functionality
- **Playwright**: Chromium browser is installed for JavaScript rendering but may have limited system dependencies in the Replit environment

## User Preferences
None specified yet.
