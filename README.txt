Iva 2.0 Reality Layer — Fintech Claim‑to‑Fact Truth Meter (MVP)

Quick start
1) Prereqs: Python 3.11+, Node (for Playwright) or use Docker
2) Setup:
   cp .env.example .env
   make dev
   make run  # FastAPI
   # or CLI:
   make cli URL=https://acmepayments.com COMPANY='Acme Payments Inc.'
3) Slack card: set SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN + SLACK_CHANNEL

Notes
- Outputs are advisory only — not legal advice.
- Respect robots.txt/TOS. Prefer official APIs.
- Store secrets in env; avoid committing secrets.

Docker
- docker compose up --build

Evaluations
- See src/iva/eval/ for harness and golden data.
