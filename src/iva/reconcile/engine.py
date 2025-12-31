from datetime import UTC, datetime
from typing import List

from ..models.claims import ClaimSet, ExtractedClaim
from ..models.recon import (
    Discrepancy,
    EvidencePointer,
    ExplanationBundle,
    FindingProvenance,
    TruthCard,
)
from ..models.sources import AdapterFinding
from .citations import confidence_from_findings
from .severity import score_severity


def _evidence_from_findings(findings: List[AdapterFinding]) -> List[EvidencePointer]:
    evidence: List[EvidencePointer] = []
    for f in findings:
        evidence.append(
            EvidencePointer(
                adapter=f.adapter,
                finding_key=f.key,
                summary=f.snippet or f.value or f.status,
                citation_urls=[c.url for c in f.citations if c.url],
            )
        )
    return evidence


def _provenance_from_findings(findings: List[AdapterFinding]) -> List[FindingProvenance]:
    provenance: List[FindingProvenance] = []
    for f in findings:
        provenance.append(
            FindingProvenance(
                adapter=f.adapter,
                finding_key=f.key,
                observed_at=f.observed_at,
                snippet=f.snippet,
                source_urls=[c.url for c in f.citations if c.url],
            )
        )
    return provenance


def _verdict_for_severity(severity: str) -> str:
    if severity == "high":
        return "escalate"
    if severity == "med":
        return "needs_review"
    return "monitor"


def _make_explanation(
    severity: str,
    confidence: float,
    findings: List[AdapterFinding],
    follow_ups: List[str],
    notes: str | None = None,
) -> ExplanationBundle:
    return ExplanationBundle(
        verdict=_verdict_for_severity(severity),
        supporting_evidence=_evidence_from_findings(findings),
        confidence=confidence,
        follow_up_actions=follow_ups,
        notes=notes,
    )


def _build_discrepancy(
    claim: ExtractedClaim,
    dtype: str,
    severity: str,
    confidence: float,
    why: str,
    expected: str,
    findings: List[AdapterFinding],
    follow_ups: List[str],
) -> Discrepancy:
    return Discrepancy(
        claim_id=claim.id,
        type=dtype,
        severity=severity,
        confidence=confidence,
        why_it_matters=why,
        expected_evidence=expected,
        findings=findings,
        claim_text=claim.claim_text,
        explanation=_make_explanation(severity, confidence, findings, follow_ups),
        provenance=_provenance_from_findings(findings),
        related_claims=[claim.id],
        related_claim_texts=[claim.claim_text] if claim.claim_text else [],
    )


def _fingerprint_findings(findings: List[AdapterFinding]) -> tuple:
    return tuple(sorted((f.adapter, f.key, f.value, f.status) for f in findings))


def _merge_or_add_discrepancy(
    discrepancies: List[Discrepancy], new_discrepancy: Discrepancy
) -> None:
    if new_discrepancy.type == "marketing_metric_unverified":
        new_fp = _fingerprint_findings(new_discrepancy.findings)
        for existing in discrepancies:
            if (
                existing.type == new_discrepancy.type
                and _fingerprint_findings(existing.findings) == new_fp
            ):
                added_claim = False
                for idx, cid in enumerate(new_discrepancy.related_claims):
                    if cid not in existing.related_claims:
                        existing.related_claims.append(cid)
                        added_claim = True
                        if idx < len(new_discrepancy.related_claim_texts):
                            text = new_discrepancy.related_claim_texts[idx]
                            if text and text not in existing.related_claim_texts:
                                existing.related_claim_texts.append(text)
                for action in new_discrepancy.explanation.follow_up_actions:
                    if action not in existing.explanation.follow_up_actions:
                        existing.explanation.follow_up_actions.append(action)
                if added_claim and new_discrepancy.claim_text:
                    extra_note = f"Also flagged claim: {new_discrepancy.claim_text}"
                    current_notes = existing.explanation.notes or ""
                    if extra_note not in current_notes:
                        existing.explanation.notes = (
                            current_notes + ("\n" if current_notes else "") + extra_note
                        ) or extra_note
                return
    discrepancies.append(new_discrepancy)


def _has_confirmed_metric(findings: List[AdapterFinding], keywords: List[str]) -> bool:
    keyword_set = [kw.lower() for kw in keywords]
    for f in findings:
        if getattr(f, "status", "") != "confirmed":
            continue
        haystack = " ".join(
            filter(
                None, [getattr(f, "key", ""), getattr(f, "value", ""), getattr(f, "snippet", "")]
            )
        ).lower()
        if any(kw in haystack for kw in keyword_set):
            return True
    return False


def reconcile(claims: ClaimSet, adapter_results: dict[str, list]) -> TruthCard:
    """
    Reconcile extracted claims against verification sources.

    This engine checks claims against multiple adapters and flags discrepancies:
    - Licensing claims vs NMLS/FINTRAC/EDGAR data
    - Partner bank claims vs public disclosures
    - Security certifications vs trust centers
    - Marketing metrics vs regulatory filings
    """
    discrepancies: List[Discrepancy] = []

    print(f"\n[RECONCILE] Processing {len(claims.claims)} claims...")

    for cl in claims.claims:
        print(f"[RECONCILE] Checking claim: [{cl.category}] {cl.claim_text[:60]}...")
        findings = []
        if cl.category == "licensing":
            findings = adapter_results.get("nmls", [])
            # Simple rule: if claim says "licensed in 30 states" but NMLS count < 20
            if cl.values and any(v.isdigit() and int(v) >= 30 for v in cl.values):
                states_list = []
                for f in findings:
                    if hasattr(f, "key") and f.key == "us_mtl_states":
                        import ast

                        try:
                            states_list = ast.literal_eval(f.value)
                        except Exception:
                            states_list = []
                if states_list and len(states_list) < 20:
                    ev = confidence_from_findings(findings)
                    sev, conf = score_severity(cl.category, "underlicensed_vs_claim", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="underlicensed_vs_claim",
                            severity=sev,
                            confidence=conf,
                            why="Compliance and go-to-market risk; may impact money movement and onboarding.",
                            expected="NMLS roster export or auditor letter with current state licenses.",
                            findings=findings,
                            follow_ups=[
                                "Request updated NMLS roster from the compliance owner.",
                                "Align marketing copy with current state coverage.",
                            ],
                        )
                    )
        if cl.category == "partner_bank":
            bank_findings = adapter_results.get("bank_partners", []) + adapter_results.get(
                "news", []
            )
            has_confirmed = any(getattr(f, "status", None) == "confirmed" for f in bank_findings)
            if not has_confirmed:
                ev = confidence_from_findings(bank_findings)
                sev, conf = score_severity(cl.category, "partner_unverified", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="partner_unverified",
                        severity=sev,
                        confidence=conf,
                        why="Sponsor bank claims require verification; affects issuing and compliance.",
                        expected="Bank partner page listing or joint press release.",
                        findings=bank_findings,
                        follow_ups=[
                            "Secure sponsor bank confirmation or contract excerpt.",
                            "Escalate to partnerships lead for attestation.",
                        ],
                    )
                )
        # SECURITY CERTIFICATIONS
        if cl.category == "security":
            sec_findings = adapter_results.get("trust_center", [])

            # Check SOC 2 claims
            if "SOC 2" in (cl.claim_text or ""):
                if any(
                    getattr(f, "key", None) == "security_txt"
                    and getattr(f, "status", None) == "not_found"
                    for f in sec_findings
                ):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category, "soc2_unsubstantiated", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="soc2_unsubstantiated",
                            severity=sev,
                            confidence=conf,
                            why="Unverified SOC 2 claim can be misleading; request auditor letter or trust center link.",
                            expected="SOC 2 Type II auditor letter (date, scope) or trust center reference.",
                            findings=sec_findings,
                            follow_ups=[
                                "Request SOC 2 auditor letter or trust center link from security lead.",
                                "Pause external messaging until attestation is confirmed.",
                            ],
                        )
                    )

            # Check ISO certifications
            if "ISO 27001" in (cl.claim_text or "") or "ISO" in (cl.claim_text or ""):
                if not any(
                    getattr(f, "key", None) == "iso_cert"
                    and getattr(f, "status", None) == "confirmed"
                    for f in sec_findings
                ):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category, "iso_unverified", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="iso_unverified",
                            severity=sev,
                            confidence=conf,
                            why="ISO certification claims should be verifiable through certificate registries.",
                            expected="ISO certificate number or listing in certification body database.",
                            findings=sec_findings,
                            follow_ups=[
                                "Collect ISO certificate ID and certification body from security team.",
                                "Update claim copy with verified scope and coverage.",
                            ],
                        )
                    )

            # Check PCI DSS claims
            if "PCI" in (cl.claim_text or ""):
                ev = confidence_from_findings(sec_findings)
                sev, conf = score_severity(cl.category, "pci_requires_verification", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="pci_requires_verification",
                        severity=sev,
                        confidence=conf,
                        why="PCI DSS compliance level should be verified with QSA attestation.",
                        expected="PCI DSS Attestation of Compliance (AOC) or QSA letter with level and date.",
                        findings=sec_findings,
                        follow_ups=[
                            "Request current AOC or QSA attestation letter.",
                            "Confirm PCI scope with payments ops stakeholder.",
                        ],
                    )
                )

        # MARKETING CLAIMS - Flag unverifiable or exaggerated claims
        if cl.category == "marketing":
            market_findings = (
                adapter_results.get("edgar", [])
                + adapter_results.get("news", [])
                + adapter_results.get("press_metrics", [])
            )
            kind_text = " ".join(filter(None, [cl.claim_kind, cl.claim_text])).lower()

            # Check customer count claims - only flag if NOT confirmed
            if "customer" in kind_text or "user" in kind_text:
                has_confirmed = _has_confirmed_metric(
                    market_findings, ["customer", "user", "merchant"]
                )
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category, "marketing_metric_unverified", ev)
                    new_disc = _build_discrepancy(
                        claim=cl,
                        dtype="marketing_metric_unverified",
                        severity=sev,
                        confidence=conf,
                        why="Customer counts are often marketing puffery; verify against SEC filings or audited reports.",
                        expected="SEC 10-K/10-Q user metrics or audited customer count statement.",
                        findings=market_findings,
                        follow_ups=[
                            "Request audited customer count from finance or strategy.",
                            "Replace claim with certified figures before publication.",
                        ],
                    )
                    _merge_or_add_discrepancy(discrepancies, new_disc)

            # Check transaction volume claims - only flag if NOT confirmed
            if any(word in kind_text for word in ["volume", "transaction", "processed", "payment"]):
                has_confirmed = _has_confirmed_metric(
                    market_findings, ["volume", "payment", "processed", "gmv"]
                )
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category, "marketing_metric_unverified", ev)
                    new_disc = _build_discrepancy(
                        claim=cl,
                        dtype="marketing_metric_unverified",
                        severity=sev,
                        confidence=conf,
                        why="Transaction volumes should be verified against regulatory filings or audited statements.",
                        expected="SEC filing with payment volume metrics or press release with audited figures.",
                        findings=market_findings,
                        follow_ups=[
                            "Gather audited payment volume from finance or data team.",
                            "Escalate marketing claim for revision until figures are confirmed.",
                        ],
                    )
                    _merge_or_add_discrepancy(discrepancies, new_disc)

            # Check vague claims like "leading", "fastest"
            vague_words = ["leading", "fastest", "best", "#1", "top", "premier"]
            if any(word in (cl.claim_text or "").lower() for word in vague_words):
                ev = confidence_from_findings(market_findings)
                sev, conf = score_severity(cl.category, "vague_marketing_claim", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="vague_marketing_claim",
                        severity=sev,
                        confidence=conf,
                        why="Superlative marketing claims ('leading', 'best') are subjective and often unsubstantiated.",
                        expected="Independent market research, industry report, or specific metric defining 'leading' status.",
                        findings=market_findings,
                        follow_ups=[
                            "Swap subjective superlatives for measurable metrics.",
                            "Attach third-party research or market share data if claim persists.",
                        ],
                    )
                )

        # REGULATORY CLAIMS
        if cl.category == "regulatory":
            reg_findings = adapter_results.get("cfpb", []) + adapter_results.get("edgar", [])

            # Check SEC registration claims
            if "SEC" in (cl.claim_text or ""):
                # Check for confirmed CIK or confirmed company name from real EDGAR adapter
                sec_filings = [
                    f
                    for f in reg_findings
                    if getattr(f, "key", None) in ["edgar_cik", "edgar_company_name"]
                ]
                if not sec_filings or all(
                    getattr(f, "status", None) != "confirmed" for f in sec_filings
                ):
                    ev = confidence_from_findings(reg_findings)
                    sev, conf = score_severity(cl.category, "regulatory_claim_unverified", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="regulatory_claim_unverified",
                            severity=sev,
                            confidence=conf,
                            why="SEC registration can be verified through EDGAR; false claims are serious violations.",
                            expected="CIK number and EDGAR filing history for RIA, BD, or other registration.",
                            findings=reg_findings,
                            follow_ups=[
                                "Confirm SEC registration status and obtain CIK from legal.",
                                "Update marketing and disclosures if registration is absent.",
                            ],
                        )
                    )

        # COMPLIANCE CLAIMS
        if cl.category == "compliance":
            comp_findings = adapter_results.get("trust_center", []) + adapter_results.get(
                "edgar", []
            )

            # Check AML/KYC claims
            if any(term in (cl.claim_text or "").upper() for term in ["AML", "KYC", "BSA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category, "compliance_program_mentioned", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="compliance_program_mentioned",
                        severity=sev,
                        confidence=conf,
                        why="AML/KYC programs should be documented and verifiable; vague mentions are red flags.",
                        expected="AML policy document, compliance program description, or regulatory examination results.",
                        findings=comp_findings,
                        follow_ups=[
                            "Request AML/KYC policy pack from compliance.",
                            "Ensure public statements reflect actual program status.",
                        ],
                    )
                )

            # Check GDPR/CCPA claims
            if any(term in (cl.claim_text or "").upper() for term in ["GDPR", "CCPA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category, "privacy_compliance_claim", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="privacy_compliance_claim",
                        severity=sev,
                        confidence=conf,
                        why="Privacy compliance should be documented in privacy policy with specific measures.",
                        expected="Privacy policy with GDPR/CCPA-specific rights, DPO contact, or privacy certification.",
                        findings=comp_findings,
                        follow_ups=[
                            "Obtain privacy compliance documentation from legal.",
                            "Clarify public claim with exact scope of GDPR/CCPA coverage.",
                        ],
                    )
                )

        # FINANCIAL PERFORMANCE CLAIMS (for public companies)
        if cl.category == "financial_performance":
            edgar_findings = adapter_results.get("edgar_filings", [])

            # Check revenue claims
            claim_text_lower = (cl.claim_text or "").lower()
            if any(term in claim_text_lower for term in ["revenue", "sales", "$"]):
                # Extract numeric value from claim if present
                claim_value = None
                if cl.values:
                    for v in cl.values:
                        # Try to extract dollar amounts
                        if "$" in v or "billion" in v.lower() or "million" in v.lower():
                            claim_value = v
                            break

                # Check if we have EDGAR revenue data
                edgar_revenue = None
                for f in edgar_findings:
                    if getattr(f, "key", "") == "edgar_revenue_annual":
                        try:
                            edgar_revenue = float(getattr(f, "value", "0"))
                            break
                        except (ValueError, TypeError):
                            pass

                if edgar_revenue and claim_value:
                    # If claim specifies a value, flag for manual review
                    # (exact matching would require parsing claim values more intelligently)
                    # Only flag if we have strong evidence (EDGAR data exists) to suggest verification is needed
                    ev = confidence_from_findings(edgar_findings)
                    # Use lower severity since we have EDGAR data - this is just a verification reminder
                    sev, conf = score_severity(cl.category, "revenue_claim_verification_needed", ev)
                    # Override to lower severity since we're just asking for verification, not flagging a problem
                    sev = "low" if sev == "med" else sev
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="revenue_claim_verification_needed",
                            severity=sev,
                            confidence=conf,
                            why="Revenue claims should match SEC filings; verify that website claim aligns with latest filing data.",
                            expected=f"SEC 10-K/10-Q filing showing revenue figure matching website claim (EDGAR shows ${edgar_revenue:,.0f}).",
                            findings=edgar_findings,
                            follow_ups=[
                                "Verify revenue figure matches latest SEC filing.",
                                "Update website if claim is outdated or incorrect.",
                            ],
                        )
                    )
                elif not edgar_revenue and claim_value:
                    # Revenue claim but no EDGAR data found
                    ev = confidence_from_findings(edgar_findings)
                    sev, conf = score_severity(cl.category, "revenue_claim_unverified", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="revenue_claim_unverified",
                            severity=sev,
                            confidence=conf,
                            why="Public company revenue claims should be verifiable against SEC filings.",
                            expected="SEC 10-K/10-Q filing with revenue figures.",
                            findings=edgar_findings,
                            follow_ups=[
                                "Verify company is public and SEC filings are accessible.",
                                "Ensure revenue claim matches latest SEC filing.",
                            ],
                        )
                    )

            # Check profit/loss claims
            if any(
                term in claim_text_lower
                for term in ["profit", "income", "loss", "profitable", "earnings"]
            ):
                edgar_net_income = None
                for f in edgar_findings:
                    if getattr(f, "key", "") == "edgar_net_income_annual":
                        try:
                            edgar_net_income = float(getattr(f, "value", "0"))
                            break
                        except (ValueError, TypeError):
                            pass

                if edgar_net_income is not None:
                    # Check if claim contradicts filing (e.g., claims profitable but filing shows loss)
                    claims_profitable = any(
                        term in claim_text_lower for term in ["profitable", "profit", "positive"]
                    )
                    if claims_profitable and edgar_net_income < 0:
                        ev = confidence_from_findings(edgar_findings)
                        sev, conf = score_severity(
                            cl.category, "profitability_claim_contradicts_filing", ev
                        )
                        discrepancies.append(
                            _build_discrepancy(
                                claim=cl,
                                dtype="profitability_claim_contradicts_filing",
                                severity="high",
                                confidence=conf,
                                why="Website claims profitability but SEC filing shows net loss. This is a serious discrepancy.",
                                expected=f"SEC filing showing net income matching website claim (filing shows ${edgar_net_income:,}).",
                                findings=edgar_findings,
                                follow_ups=[
                                    "Immediately update website to reflect accurate financial status.",
                                    "Escalate to legal/compliance if claim was intentionally misleading.",
                                ],
                            )
                        )

        # MARKET POSITION CLAIMS (for public companies)
        if cl.category == "market_position":
            edgar_findings = adapter_results.get("edgar_filings", [])
            market_findings = edgar_findings + adapter_results.get("news", [])

            # Check market leadership/superlative claims
            vague_words = [
                "leading",
                "#1",
                "largest",
                "fastest",
                "best",
                "top",
                "premier",
                "dominant",
            ]
            if any(word in (cl.claim_text or "").lower() for word in vague_words):
                ev = confidence_from_findings(market_findings)
                sev, conf = score_severity(cl.category, "market_position_unsubstantiated", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="market_position_unsubstantiated",
                        severity=sev,
                        confidence=conf,
                        why="Market position claims should be supported by independent research, market share data, or industry reports.",
                        expected="Third-party market research, industry analyst report, or quantifiable market share metric.",
                        findings=market_findings,
                        follow_ups=[
                            "Request supporting data from marketing/product team.",
                            "Replace subjective claims with specific, verifiable metrics.",
                        ],
                    )
                )

            # Check market share claims with specific percentages
            if "%" in (cl.claim_text or "") and any(
                term in (cl.claim_text or "").lower() for term in ["market share", "share"]
            ):
                ev = confidence_from_findings(market_findings)
                sev, conf = score_severity(
                    cl.category, "market_share_claim_verification_needed", ev
                )
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="market_share_claim_verification_needed",
                        severity=sev,
                        confidence=conf,
                        why="Market share percentages should be verifiable through industry reports or financial filings.",
                        expected="Market research report or industry analysis supporting the market share claim.",
                        findings=market_findings,
                        follow_ups=[
                            "Obtain source documentation for market share figure.",
                            "Ensure claim includes attribution to research source.",
                        ],
                    )
                )

        # FORWARD-LOOKING STATEMENTS (for public companies)
        if cl.category == "forward_looking":
            edgar_findings = adapter_results.get("edgar_filings", [])

            # Check if forward-looking statements have proper disclaimers
            forward_looking_keywords = [
                "expect",
                "believe",
                "anticipate",
                "plan",
                "forecast",
                "project",
                "guidance",
                "target",
            ]
            has_disclaimer = any(
                term in (cl.claim_text or "").lower()
                for term in ["forward-looking", "cautionary", "safe harbor", "risks"]
            )

            if (
                any(kw in (cl.claim_text or "").lower() for kw in forward_looking_keywords)
                and not has_disclaimer
            ):
                ev = confidence_from_findings(edgar_findings)
                sev, conf = score_severity(cl.category, "forward_looking_missing_disclaimer", ev)
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="forward_looking_missing_disclaimer",
                        severity=sev,
                        confidence=conf,
                        why="Forward-looking statements should include safe harbor disclaimers to protect against liability.",
                        expected="Forward-looking statement with appropriate safe harbor language and risk disclaimers.",
                        findings=edgar_findings,
                        follow_ups=[
                            "Add safe harbor disclaimer to forward-looking statements.",
                            "Review with legal team to ensure compliance with SEC guidance.",
                        ],
                    )
                )

            # Check guidance claims - flag for verification that it matches SEC filings
            # Note: We can't easily parse filing content to verify exact match, so we flag for manual review
            if "guidance" in (cl.claim_text or "").lower() and any(
                term in (cl.claim_text or "").lower()
                for term in ["$", "revenue", "earnings", "forecast"]
            ):
                # Check if we have recent filings available
                has_recent_filings = any(
                    "edgar_8k" in (getattr(f, "key", "") or "")
                    or "edgar_latest_10q" in (getattr(f, "key", "") or "")
                    or "edgar_latest_10k" in (getattr(f, "key", "") or "")
                    for f in edgar_findings
                )
                if has_recent_filings:
                    ev = confidence_from_findings(edgar_findings)
                    sev, conf = score_severity(cl.category, "guidance_verification_needed", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="guidance_verification_needed",
                            severity=sev,
                            confidence=conf,
                            why="Financial guidance on website should match what's disclosed in SEC filings to avoid confusion.",
                            expected="Verification that website guidance matches latest 8-K or 10-Q/10-K guidance disclosure.",
                            findings=edgar_findings,
                            follow_ups=[
                                "Verify guidance matches what's disclosed in SEC filings.",
                                "Ensure website guidance is synchronized with investor communications.",
                            ],
                        )
                    )

        # LITIGATION CLAIMS (for public companies)
        if cl.category == "litigation":
            edgar_findings = adapter_results.get("edgar_filings", [])

            # Check if litigation is mentioned on website
            litigation_keywords = [
                "lawsuit",
                "litigation",
                "legal action",
                "sued",
                "complaint",
                "dispute",
                "settlement",
            ]
            if any(kw in (cl.claim_text or "").lower() for kw in litigation_keywords):
                # Check if Item 3 (Legal Proceedings) section exists in 10-K
                has_item_3 = any(
                    getattr(f, "key", "") == "edgar_10k_item_3_legal" for f in edgar_findings
                )

                if has_item_3:
                    ev = confidence_from_findings(edgar_findings)
                    sev, conf = score_severity(
                        cl.category, "litigation_disclosure_verification_needed", ev
                    )
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="litigation_disclosure_verification_needed",
                            severity=sev,
                            confidence=conf,
                            why="Litigation mentioned on website should match disclosures in SEC filings (Item 3 of 10-K).",
                            expected="10-K Item 3 (Legal Proceedings) section confirming or describing the litigation.",
                            findings=edgar_findings,
                            follow_ups=[
                                "Verify litigation claim matches 10-K Item 3 disclosure.",
                                "Ensure website statements don't contradict SEC filings.",
                            ],
                        )
                    )
                else:
                    ev = confidence_from_findings(edgar_findings)
                    sev, conf = score_severity(cl.category, "litigation_claim_missing_filing", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="litigation_claim_missing_filing",
                            severity="high",
                            confidence=conf,
                            why="Public companies must disclose material litigation in SEC filings. Website mention without filing disclosure may indicate incomplete disclosure.",
                            expected="10-K Item 3 (Legal Proceedings) section or 8-K filing disclosing the litigation.",
                            findings=edgar_findings,
                            follow_ups=[
                                "Verify litigation is properly disclosed in SEC filings.",
                                "Escalate to legal/compliance if material litigation is missing from filings.",
                            ],
                        )
                    )

        # BUSINESS METRICS CLAIMS (for public companies)
        if cl.category == "business_metrics":
            edgar_findings = adapter_results.get("edgar_filings", [])
            market_findings = edgar_findings + adapter_results.get("press_metrics", [])

            # Check user/customer count claims
            claim_text_lower = (cl.claim_text or "").lower()
            if any(
                term in claim_text_lower for term in ["user", "customer", "merchant", "account"]
            ):
                has_confirmed = _has_confirmed_metric(
                    market_findings, ["user", "customer", "merchant", "account"]
                )
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category, "business_metric_unverified", ev)
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="business_metric_unverified",
                            severity=sev,
                            confidence=conf,
                            why="Business metrics should be verifiable through SEC filings, press releases, or audited statements.",
                            expected="SEC filing (10-K/10-Q) or verified press release with user/customer metrics.",
                            findings=market_findings,
                            follow_ups=[
                                "Request verified user/customer count from finance or product team.",
                                "Ensure claim matches what's disclosed in SEC filings or official communications.",
                            ],
                        )
                    )

        # MATERIAL EVENTS CLAIMS (for public companies)
        if cl.category == "material_events":
            edgar_findings = adapter_results.get("edgar_filings", [])
            press_release_findings = adapter_results.get("press_releases", [])

            # Check for M&A, partnerships, executive changes
            material_keywords = [
                "acquired",
                "merger",
                "partnership",
                "ceo",
                "executive",
                "leadership",
                "agreement",
            ]
            if any(kw in (cl.claim_text or "").lower() for kw in material_keywords):
                # Check if there's a recent 8-K filing
                # Note: We check last 5 8-K filings; if event is older, this may not catch it
                # but material events should be filed within 4 business days per SEC rules
                has_recent_8k = any(
                    "edgar_8k" in (getattr(f, "key", "") or "") for f in edgar_findings
                )

                # Also check press releases
                has_press_release = any(
                    "press_release" in (getattr(f, "key", "") or "")
                    and getattr(f, "status", "") == "confirmed"
                    for f in press_release_findings
                )

                if not has_recent_8k and not has_press_release:
                    ev = confidence_from_findings(edgar_findings + press_release_findings)
                    sev, conf = score_severity(cl.category, "material_event_missing_8k", ev)
                    # Material events without 8-K filings are high severity compliance issues
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="material_event_missing_8k",
                            severity="high",
                            confidence=conf,
                            why="Material events (M&A, executive changes, partnerships) typically require 8-K filings within 4 business days per SEC rules.",
                            expected="8-K filing or press release disclosing the material event within required timeframe.",
                            findings=edgar_findings + press_release_findings,
                            follow_ups=[
                                "Verify material event is properly disclosed in 8-K filing or press release.",
                                "Check if event occurred recently enough that 8-K should already be filed.",
                                "Escalate to legal/compliance if required 8-K filing is missing.",
                            ],
                        )
                    )

        # EARNINGS CALLS RECONCILIATION (Phase 3)
        # Check if forward-looking statements match earnings call transcripts
        if cl.category == "forward_looking":
            earnings_findings = adapter_results.get("earnings_calls", [])

            # Check if earnings transcripts are available
            has_transcripts = any(
                "earnings_transcript" in (getattr(f, "key", "") or "")
                and getattr(f, "status", "") == "confirmed"
                for f in earnings_findings
            )

            if has_transcripts:
                # Forward-looking statements should align with earnings call guidance
                forward_looking_keywords = [
                    "expect",
                    "believe",
                    "anticipate",
                    "plan",
                    "forecast",
                    "project",
                    "guidance",
                    "target",
                ]
                if any(kw in (cl.claim_text or "").lower() for kw in forward_looking_keywords):
                    ev = confidence_from_findings(earnings_findings)
                    sev, conf = score_severity(
                        cl.category, "forward_looking_earnings_verification_needed", ev
                    )
                    discrepancies.append(
                        _build_discrepancy(
                            claim=cl,
                            dtype="forward_looking_earnings_verification_needed",
                            severity=sev,
                            confidence=conf,
                            why="Forward-looking statements on website should align with what was disclosed in earnings call transcripts.",
                            expected="Verification that website forward-looking statement matches guidance provided in earnings call.",
                            findings=earnings_findings,
                            follow_ups=[
                                "Review earnings call transcripts to verify forward-looking statement alignment.",
                                "Ensure website claims match what executives stated in earnings calls.",
                            ],
                        )
                    )

        # PRESS RELEASE RECONCILIATION (Phase 3)
        # Compare website claims against official press releases
        # Note: This is a simplified check - full implementation would parse press release content
        # For now, we only flag material events since those are most likely to have press releases
        press_release_findings = adapter_results.get("press_releases", [])

        if cl.category == "material_events" and press_release_findings:
            # Material events should have corresponding press releases
            # Check if we found press releases in recent filings
            has_recent_pr = any(
                "press_release" in (getattr(f, "key", "") or "")
                and getattr(f, "status", "") == "confirmed"
                for f in press_release_findings
            )

            if not has_recent_pr:
                # Material event claim but no recent press release found
                ev = confidence_from_findings(press_release_findings)
                sev, conf = score_severity(
                    cl.category, "material_event_press_release_verification_needed", ev
                )
                # Lower severity since press releases may exist elsewhere
                sev = "low"
                discrepancies.append(
                    _build_discrepancy(
                        claim=cl,
                        dtype="material_event_press_release_verification_needed",
                        severity=sev,
                        confidence=conf,
                        why="Material events typically have corresponding press releases or official announcements.",
                        expected="Press release or official announcement confirming the material event.",
                        findings=press_release_findings,
                        follow_ups=[
                            "Verify material event was announced via press release or official channel.",
                            "Ensure website claims are consistent with official communications.",
                        ],
                    )
                )

    # HISTORICAL TRACKING RECONCILIATION (Phase 3)
    # Flag claims that changed significantly from previous extractions (once per analysis)
    historical_findings = adapter_results.get("historical_tracking", [])

    if historical_findings:
        # Check if there are modified or removed claims
        has_modified = any(
            "historical_modified_claims" in (getattr(f, "key", "") or "")
            for f in historical_findings
        )
        has_removed = any(
            "historical_removed_claims" in (getattr(f, "key", "") or "")
            for f in historical_findings
        )

        if has_modified or has_removed:
            # Add a single informational discrepancy about historical changes
            ev = confidence_from_findings(historical_findings)
            sev, conf = score_severity("marketing", "historical_claims_changed", ev)
            # Lower severity - informational
            sev = "low"
            # Create a summary claim for historical changes
            summary_claim = ExtractedClaim(
                id="historical_summary",
                category="marketing",
                claim_text=f"Historical tracking detected {len(historical_findings)} change(s) in claims compared to previous extraction.",
            )
            discrepancies.append(
                _build_discrepancy(
                    claim=summary_claim,
                    dtype="historical_claims_changed",
                    severity=sev,
                    confidence=conf,
                    why="Claims have changed compared to previous extraction. Verify if changes are intentional and accurate.",
                    expected="Review of historical claim changes to ensure accuracy.",
                    findings=historical_findings,
                    follow_ups=[
                        "Review claim changes in historical tracking.",
                        "Verify that claim changes are intentional and accurate.",
                    ],
                )
            )
    sev_counts = {"high": 0, "med": 0, "low": 0}
    for d in discrepancies:
        sev_counts[d.severity] += 1
    severity_summary = f"H:{sev_counts['high']} • M:{sev_counts['med']} • L:{sev_counts['low']}"
    overall_confidence = min(1.0, 0.5 + 0.1 * len(discrepancies))
    return TruthCard(
        url=claims.url,
        company=claims.company,
        severity_summary=severity_summary,
        discrepancies=discrepancies,
        overall_confidence=overall_confidence,
        generated_at=datetime.now(UTC),
    )
