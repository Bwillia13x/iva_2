# Iva 3.0 Implementation Roadmap

**Updated**: October 31, 2025  
**Horizon**: 24 months (Nov 2025 – Oct 2027)  
**Objective**: Execute the strategic pillars in `PRODUCT_VISION.md` to transform Iva 2.0 into the Iva 3.0 Due Diligence Operating System.

---

## 0. Program Structure & Governance

- **Steering Committee**: CEO (chair), Head of Product, CTO, VP Sales, VP Customer Success
- **Program Management Office (PMO)**: 1 full-time lead + 2 program coordinators
- **Core Workstreams** (mapped to vision pillars):
  1. Platform & Tenant Foundation (Pillar 1)
  2. Monitoring & Alerts (Pillar 2)
  3. Predictive Intelligence & Trust Score (Pillar 3)
  4. Data Network & Graph (Pillar 4 & 9)
  5. Copilot Decision Support (Pillar 6)
  6. Compliance-as-a-Service (Pillar 7)
  7. API & Integrations + Mobile (Pillars 8 & 10)
  8. Vertical Expansion (Pillar 5)
- **Cadence**: Bi-weekly cross-workstream sync, monthly leadership review, quarterly roadmap reset
- **Tooling**: Linear (execution), Notion (documentation), Looker (KPIs)

---

## 1. Phase Timeline Overview

```text
| Phase | Dates (target)      | Theme                                      | Pillars            |
|-------|---------------------|--------------------------------------------|--------------------|
| P0    | Nov 2025 – Jan 2026 | Program kickoff & technical readiness      | All (foundations)  |
| P1    | Jan 2026 – Mar 2026 | Multi-tenant platform foundation           | 1, 8 (core API)    |
| P2    | Apr 2026 – Jun 2026 | Real-time monitoring & alerting            | 2                  |
| P3    | Jul 2026 – Sep 2026 | Predictive intelligence & trust scoring    | 3                  |
| P4    | Oct 2026 – Dec 2026 | Network data & regulatory graph            | 4, 9               |
| P5    | Jan 2027 – Mar 2027 | Decision support copilot & recommendations | 6                  |
| P6    | Apr 2027 – Jun 2027 | Compliance-as-a-service & API scaling      | 7, 8               |
| P7    | Jul 2027 – Oct 2027 | Vertical expansion & mobile experiences    | 5, 10              |
```

Each phase includes engineering sprints, design, GTM enablement, security review, and a beta → GA launch process.

---

## 2. Phase Details & Deliverables

### Phase 0: Program Kickoff & Technical Readiness (Nov 2025 – Jan 2026)

**Goals**: Align teams, harden infra, prepare codebase for multi-tenant + real-time workloads.

- **Deliverables**
  - Product requirements baseline for each pillar (PRDs approved)
  - Architecture doc updates for platform, monitoring, graph, and copilot flows
  - DevOps upgrades: IaC (Terraform), staging environment parity, CI/CD hardening, observability baselines
  - Data governance plan (PII classification, retention policies, compliance checklist)
  - PMO launch: dashboards for roadmap, staffing, budget, OKRs
- **Dependencies**: Existing Iva 2.0 services remain stable; identify refactor debt
- **Exit Criteria**: All PRDs signed, infra readiness scored ≥80%, hiring plan locked

### Phase 1: Multi-Tenant Platform Foundation (Jan 2026 – Mar 2026)

**Goals**: Enable workspaces, RBAC, collaboration, core API gateway.

- **Engineering**
  - Workspace & account models (`Workspace`, `OrgMembership`, `Role`)
  - Auth0 multi-tenant configuration + SSO support
  - Role-based permissions (Analyst/Senior/Partner/Admin)
  - Commenting, assignments, activity stream, audit logging
  - FastAPI gateway restructuring, versioned REST API, rate limiting
- **Product & Design**
  - Workspace admin console (seat mgmt, billing hooks)
  - Updated UI for pipeline and status tracking
- **GTM/OPS**
  - Pricing & packaging update (Starter/Professional/Enterprise rollout plan)
  - Beta customer selection (10 design partners)
- **Metrics**: Tenant creation lead time <10 min; workspace NPS baseline
- **Exit Criteria**: 10 tenants live in beta; SOC2 control design initiated

### Phase 2: Real-Time Monitoring & Alerts (Apr 2026 – Jun 2026)

**Goals**: Always-on intelligence pipeline (licenses, filings, news, partners).

- **Engineering**
  - Monitoring job scheduler (Celery beat + Redis) w/ SLA <1h
  - Source adapters for licenses (NMLS, FINTRAC), filings (SEC 8-K/10-Q), news sentiment, regulatory updates
  - Alert service with severity, dedupe, routing (Slack, email, webhook)
  - Alert dashboard + acknowledgement workflow
  - Historical baseline storage to enable diffing
- **Data Science**
  - News sentiment pipeline (LLM classification + scoring)
  - Alert prioritization heuristics (critical/high/medium/low)
- **GTM**
  - Monitoring packaging (per-plan limits), sales collateral, onboarding playbook
- **Testing**: Load tests (1k companies, 5k alerts/day), on-call runbook
- **Exit Criteria**: ≥95% alerts within SLA, beta customers adopt monitoring as daily driver

### Phase 3: Predictive Intelligence & Trust Score (Jul 2026 – Sep 2026)

**Goals**: Deliver trust score, trend detection, risk prediction models.

- **Engineering/Data**
  - Trust score computation engine (batch + on-demand) w/ component breakdown
  - Time-decay scoring, peer benchmarking using aggregated dataset
  - Trend analytics dashboards (license momentum, partner stability, filing quality)
  - Feature store for risk models (revocations, enforcement likelihood)
  - Confidence-adjusted discrepancy scoring pipeline
- **Research**
  - Model evaluation framework (precision/recall, bias audit)
  - Human-in-the-loop workflow for high-severity overrides
- **Product**
  - UX for trust score, percentile, trend state (improving/stable/declining)
  - Executive summary card in UI, export to PDF/API
- **Exit Criteria**: Trust score accuracy validated vs analyst baseline (±5 pts), GA for beta cohort

### Phase 4: Network Effects & Regulatory Graph (Oct 2026 – Dec 2026)

**Goals**: Aggregate findings, enable benchmarks, launch Neo4j relationship graph.

- **Engineering**
  - Privacy-preserving aggregation service (k-anonymity, opt-in)
  - Benchmark API (`/api/benchmarks/{category}`) with peer group filters
  - Neo4j Aura deployment, ETL pipelines from analyses to graph schema
  - Visualization layer (market maps, partner network, regulatory timeline)
  - Syndicate sharing permissions + audit trails
- **Compliance**
  - Data sharing policy, consent management, legal review
- **GTM**
  - Premium benchmarking tier definition, pricing update, case studies
- **Exit Criteria**: 500+ analyses contributing to benchmarks; graph queries <500ms; 3 design partners using syndicate sharing

### Phase 5: Decision Support Copilot (Jan 2027 – Mar 2027)

**Goals**: Transform findings into recommendations, IC memo automation.

- **Engineering/ML**
  - Prompt library + LLM orchestration (`DealContext`, `Recommendation` classes)
  - Deal scoring, pricing impact, term-sheet clause generator, risk playbooks, IC memo template
  - Feedback capture + fine-tuning loop; fallback heuristics for LLM downtime
- **Product**
  - Copilot UI (chat-style + structured outputs)
  - Explainability features (evidence linking, comparable deals reference list)
- **Operations**
  - Review board for high-severity recommendations; compliance sign-off
- **Metrics**: Analyst satisfaction >80%; response latency <30s; reduction in manual memo time by 50%
- **Exit Criteria**: Copilot GA for Professional+ plans; legal/compliance approval

### Phase 6: Compliance-as-a-Service & API Scaling (Apr 2027 – Jun 2027)

**Goals**: Serve portfolio companies, expand API ecosystem.

- **Engineering**
  - Compliance portal UI (portfolio self-service, action items, badges)
  - Renewal calendar, task assignment, SLA tracking
  - Verification badge API (trust score ≥80, scan freshness <30 days)
  - API usage scaling (OAuth 2.0, API key mgmt, usage metering, billing integration)
- **GTM**
  - Dual-sided pricing (investor + portfolio company bundles)
  - Success playbooks for managed compliance service
- **Exit Criteria**: 25 portfolio companies onboarded; API utilization 10k calls/day; badge program pilot launched

### Phase 7: Vertical Expansion & Mobile Experience (Jul 2027 – Oct 2027)

**Goals**: Enter first new vertical (HealthTech), ship mobile + browser extension.

- **Engineering**
  - Vertical adapter framework cleanup, vertical-specific prompts (`extract_healthtech.prompt` etc)
  - HealthTech data sources (FDA MAUDE, ClinicalTrials.gov, OIG)
  - React Native mobile app MVP (trust score reader, alerts, quick scan)
  - Browser extension (trust overlay, context menu verification)
  - Voice assistant skill (Alexa/Google) proof-of-concept
- **GTM**
  - Industry partnerships (Digital Health Coalition pilot)
  - Vertical-specific marketing collateral, pricing add-on
- **Exit Criteria**: 3 HealthTech pilot customers, mobile app retention >40% weekly, extension MAU ≥500

---

## 3. Cross-Cutting Workstreams

- **Security & Compliance**
  - SOC2 Type I (Phase 1), SOC2 Type II (Phase 4), ISO 27001 readiness (Phase 6)
  - Data residency strategy for EU/UK markets (prep Phase 7)
- **Data Platform**
  - Centralized logging (Datadog), data lake (S3 + Glue), BI dashboards (Looker)
  - Feature store + model registry (MLflow) for predictive models
- **Quality & Testing**
  - Shift-left: contract tests for adapters, synthetic monitoring for APIs
  - End-to-end scenario coverage per phase before GA
- **Hiring Plan**
  - Headcount additions by function (Eng, DS, Product, CS) aligned with phases
  - Contractor/partner sourcing for vertical expertise
- **Customer Success & Support**
  - Training modules, certification program for analysts (Phase 5)
  - Support SLA definitions, escalation matrix (Phase 1)

---

## 4. Milestones & KPIs

```text
| Milestone                           | Target Date | KPI Snapshot                                        |
|------------------------------------|-------------|-----------------------------------------------------|
| Multi-tenant GA                    | Mar 2026    | 50 paying workspaces; Workspace NPS ≥ 40            |
| Monitoring adoption                | Jun 2026    | ≥70% DAU interacting with alerts; SLA ≥95% met      |
| Trust score launch                 | Sep 2026    | 60% analyses include trust score; accuracy ±5 pts   |
| Benchmark & graph release          | Dec 2026    | 200 benchmark queries/wk; 100 graph queries/day     |
| Copilot GA                         | Mar 2027    | Analysts save 50% memo time; satisfaction ≥80%      |
| Compliance portal GA               | Jun 2027    | 25 portfolio cos; badge attach rate ≥40%            |
| HealthTech vertical launch         | Oct 2027    | 3 paying pilots; ARR +$1M incremental               |
| Mobile + extensions active users   | Oct 2027    | 1k MAU mobile; 500 MAU extension                    |
```

---

## 5. Dependencies & Risk Mitigation

- **LLM Provider Dependence**: Multi-model fallback (OpenAI, Anthropic, internal) starting Phase 3; maintain prompt test suites.
- **Data Source Rate Limits**: Implement caching, staggered job execution, and compliance-friendly user-agent policies.
- **Security & Compliance**: Embed security review each sprint; automated secrets scanning; regular pen tests (Phase 1 onwards).
- **Change Management**: Dedicated customer success pods for migrations; communication plan for every GA launch.
- **Hiring Risks**: Start recruitment in preceding phase (e.g., DS hires in Phase 2 for Phase 3 work).

---

## 6. Budget & Resource Outline (High Level)

- **Engineering**: +12 FTE over 24 months (6 backend, 3 frontend, 2 data/ML, 1 mobile)
- **Product/Design**: +4 FTE (2 PMs, 2 designers)
- **Data Science/Analytics**: +3 FTE (trust score, risk models, benchmarks)
- **Customer Success & Support**: +5 FTE (phased with GA milestones)
- **Cloud/Infra**: Budget scaling from $35K → $120K monthly (monitoring, Neo4j, LLM usage)
- **Contingency**: 15% buffer for vendor costs and vertical data licensing

---

## 7. Integration of Existing Public Company Roadmap

- Fold completed public-company adapters (EDGAR, earnings calls, press releases, peer comparison) into Phase 1 platform refactor and Phase 2 monitoring.
- Align outstanding testing items with Phase 0 QA workstream to close gaps before multi-tenant migration.
- Reuse alerting infrastructure from public roadmap as baseline for Phase 2, ensuring SLA upgrades and tenant-aware scoping.

---

## 8. Next Steps

1. Approve this roadmap at the November 2025 steering meeting.
2. Launch Phase 0 PMO onboarding and infra hardening immediately.
3. Initiate hiring process for Phase 1 engineers and product roles (lead times 60-90 days).
4. Confirm design partners for workspace beta and monitoring pilots.
5. Publish quarterly OKRs aligned with milestones above.

---

**Ready to execute.**
