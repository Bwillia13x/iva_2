from datetime import datetime, UTC
from typing import List
from ..models.claims import ClaimSet, ExtractedClaim
from ..models.recon import (
    Discrepancy,
    TruthCard,
    ExplanationBundle,
    EvidencePointer,
    FindingProvenance,
)
from ..models.sources import AdapterFinding
from .severity import score_severity
from .citations import confidence_from_findings

def _evidence_from_findings(findings: List[AdapterFinding]) -> List[EvidencePointer]:
    evidence: List[EvidencePointer] = []
    for f in findings:
        evidence.append(EvidencePointer(
            adapter=f.adapter,
            finding_key=f.key,
            summary=f.snippet or f.value or f.status,
            citation_urls=[c.url for c in f.citations if c.url],
        ))
    return evidence

def _provenance_from_findings(findings: List[AdapterFinding]) -> List[FindingProvenance]:
    provenance: List[FindingProvenance] = []
    for f in findings:
        provenance.append(FindingProvenance(
            adapter=f.adapter,
            finding_key=f.key,
            observed_at=f.observed_at,
            snippet=f.snippet,
            source_urls=[c.url for c in f.citations if c.url],
        ))
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

def _build_discrepancy(claim: ExtractedClaim, dtype: str, severity: str, confidence: float, why: str, expected: str, findings: List[AdapterFinding], follow_ups: List[str]) -> Discrepancy:
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

def _merge_or_add_discrepancy(discrepancies: List[Discrepancy], new_discrepancy: Discrepancy) -> None:
    if new_discrepancy.type == "marketing_metric_unverified":
        new_fp = _fingerprint_findings(new_discrepancy.findings)
        for existing in discrepancies:
            if existing.type == new_discrepancy.type and _fingerprint_findings(existing.findings) == new_fp:
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
                        existing.explanation.notes = (current_notes + ("\n" if current_notes else "") + extra_note) or extra_note
                return
    discrepancies.append(new_discrepancy)

def _has_confirmed_metric(findings: List[AdapterFinding], keywords: List[str]) -> bool:
    keyword_set = [kw.lower() for kw in keywords]
    for f in findings:
        if getattr(f, "status", "") != "confirmed":
            continue
        haystack = " ".join(filter(None, [getattr(f, "key", ""), getattr(f, "value", ""), getattr(f, "snippet", "")])).lower()
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
            findings = adapter_results.get("nmls",[])
            # Simple rule: if claim says "licensed in 30 states" but NMLS count < 20
            if cl.values and any(v.isdigit() and int(v) >= 30 for v in cl.values):
                states_list = []
                for f in findings:
                    if hasattr(f, 'key') and f.key == "us_mtl_states":
                        import ast
                        try:
                            states_list = ast.literal_eval(f.value)
                        except Exception:
                            states_list = []
                if states_list and len(states_list) < 20:
                    ev = confidence_from_findings(findings)
                    sev, conf = score_severity(cl.category,"underlicensed_vs_claim", ev)
                    discrepancies.append(_build_discrepancy(
                        claim=cl,
                        dtype="underlicensed_vs_claim",
                        severity=sev,
                        confidence=conf,
                        why="Compliance and go-to-market risk; may impact money movement and onboarding.",
                        expected="NMLS roster export or auditor letter with current state licenses.",
                        findings=findings,
                        follow_ups=[
                            "Request updated NMLS roster from the compliance owner.",
                            "Align marketing copy with current state coverage."
                        ],
                    ))
        if cl.category == "partner_bank":
            bank_findings = adapter_results.get("bank_partners",[]) + adapter_results.get("news",[])
            has_confirmed = any(getattr(f,'status',None)=="confirmed" for f in bank_findings)
            if not has_confirmed:
                ev = confidence_from_findings(bank_findings)
                sev, conf = score_severity(cl.category,"partner_unverified", ev)
                discrepancies.append(_build_discrepancy(
                    claim=cl,
                    dtype="partner_unverified",
                    severity=sev,
                    confidence=conf,
                    why="Sponsor bank claims require verification; affects issuing and compliance.",
                    expected="Bank partner page listing or joint press release.",
                    findings=bank_findings,
                    follow_ups=[
                        "Secure sponsor bank confirmation or contract excerpt.",
                        "Escalate to partnerships lead for attestation."
                    ],
                ))
        # SECURITY CERTIFICATIONS
        if cl.category == "security":
            sec_findings = adapter_results.get("trust_center",[])
            
            # Check SOC 2 claims
            if "SOC 2" in (cl.claim_text or ""):
                if any(getattr(f,'key',None)=="security_txt" and getattr(f,'status',None)=="not_found" for f in sec_findings):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category,"soc2_unsubstantiated", ev)
                    discrepancies.append(_build_discrepancy(
                        claim=cl,
                        dtype="soc2_unsubstantiated",
                        severity=sev,
                        confidence=conf,
                        why="Unverified SOC 2 claim can be misleading; request auditor letter or trust center link.",
                        expected="SOC 2 Type II auditor letter (date, scope) or trust center reference.",
                        findings=sec_findings,
                        follow_ups=[
                            "Request SOC 2 auditor letter or trust center link from security lead.",
                            "Pause external messaging until attestation is confirmed."
                        ],
                    ))
            
            # Check ISO certifications
            if "ISO 27001" in (cl.claim_text or "") or "ISO" in (cl.claim_text or ""):
                if not any(getattr(f,'key',None)=="iso_cert" and getattr(f,'status',None)=="confirmed" for f in sec_findings):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category,"iso_unverified", ev)
                    discrepancies.append(_build_discrepancy(
                        claim=cl,
                        dtype="iso_unverified",
                        severity=sev,
                        confidence=conf,
                        why="ISO certification claims should be verifiable through certificate registries.",
                        expected="ISO certificate number or listing in certification body database.",
                        findings=sec_findings,
                        follow_ups=[
                            "Collect ISO certificate ID and certification body from security team.",
                            "Update claim copy with verified scope and coverage."
                        ],
                    ))
            
            # Check PCI DSS claims
            if "PCI" in (cl.claim_text or ""):
                ev = confidence_from_findings(sec_findings)
                sev, conf = score_severity(cl.category,"pci_requires_verification", ev)
                discrepancies.append(_build_discrepancy(
                    claim=cl,
                    dtype="pci_requires_verification",
                    severity=sev,
                    confidence=conf,
                    why="PCI DSS compliance level should be verified with QSA attestation.",
                    expected="PCI DSS Attestation of Compliance (AOC) or QSA letter with level and date.",
                    findings=sec_findings,
                    follow_ups=[
                        "Request current AOC or QSA attestation letter.",
                        "Confirm PCI scope with payments ops stakeholder."
                    ],
                ))
        
        # MARKETING CLAIMS - Flag unverifiable or exaggerated claims
        if cl.category == "marketing":
            market_findings = (
                adapter_results.get("edgar",[])
                + adapter_results.get("news",[])
                + adapter_results.get("press_metrics",[])
            )
            kind_text = " ".join(filter(None, [cl.claim_kind, cl.claim_text])).lower()
            
            # Check customer count claims - only flag if NOT confirmed
            if "customer" in kind_text or "user" in kind_text:
                has_confirmed = _has_confirmed_metric(market_findings, ["customer", "user", "merchant"])
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category,"marketing_metric_unverified", ev)
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
                            "Replace claim with certified figures before publication."
                        ],
                    )
                    _merge_or_add_discrepancy(discrepancies, new_disc)
            
            # Check transaction volume claims - only flag if NOT confirmed
            if any(word in kind_text for word in ["volume", "transaction", "processed", "payment"]):
                has_confirmed = _has_confirmed_metric(market_findings, ["volume", "payment", "processed", "gmv"])
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category,"marketing_metric_unverified", ev)
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
                            "Escalate marketing claim for revision until figures are confirmed."
                        ],
                    )
                    _merge_or_add_discrepancy(discrepancies, new_disc)
            
            # Check vague claims like "leading", "fastest"
            vague_words = ["leading", "fastest", "best", "#1", "top", "premier"]
            if any(word in (cl.claim_text or "").lower() for word in vague_words):
                ev = confidence_from_findings(market_findings)
                sev, conf = score_severity(cl.category,"vague_marketing_claim", ev)
                discrepancies.append(_build_discrepancy(
                    claim=cl,
                    dtype="vague_marketing_claim",
                    severity=sev,
                    confidence=conf,
                    why="Superlative marketing claims ('leading', 'best') are subjective and often unsubstantiated.",
                    expected="Independent market research, industry report, or specific metric defining 'leading' status.",
                    findings=market_findings,
                    follow_ups=[
                        "Swap subjective superlatives for measurable metrics.",
                        "Attach third-party research or market share data if claim persists."
                    ],
                ))
        
        # REGULATORY CLAIMS
        if cl.category == "regulatory":
            reg_findings = adapter_results.get("cfpb",[]) + adapter_results.get("edgar",[])
            
            # Check SEC registration claims
            if "SEC" in (cl.claim_text or ""):
                sec_filings = [f for f in reg_findings if getattr(f,'key',None)=="edgar_search"]
                if not sec_filings or all(getattr(f,'status',None)!="confirmed" for f in sec_filings):
                    ev = confidence_from_findings(reg_findings)
                    sev, conf = score_severity(cl.category,"regulatory_claim_unverified", ev)
                    discrepancies.append(_build_discrepancy(
                        claim=cl,
                        dtype="regulatory_claim_unverified",
                        severity=sev,
                        confidence=conf,
                        why="SEC registration can be verified through EDGAR; false claims are serious violations.",
                        expected="CIK number and EDGAR filing history for RIA, BD, or other registration.",
                        findings=reg_findings,
                        follow_ups=[
                            "Confirm SEC registration status and obtain CIK from legal.",
                            "Update marketing and disclosures if registration is absent."
                        ],
                    ))
        
        # COMPLIANCE CLAIMS
        if cl.category == "compliance":
            comp_findings = adapter_results.get("trust_center",[]) + adapter_results.get("edgar",[])
            
            # Check AML/KYC claims
            if any(term in (cl.claim_text or "").upper() for term in ["AML", "KYC", "BSA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category,"compliance_program_mentioned", ev)
                discrepancies.append(_build_discrepancy(
                    claim=cl,
                    dtype="compliance_program_mentioned",
                    severity=sev,
                    confidence=conf,
                    why="AML/KYC programs should be documented and verifiable; vague mentions are red flags.",
                    expected="AML policy document, compliance program description, or regulatory examination results.",
                    findings=comp_findings,
                    follow_ups=[
                        "Request AML/KYC policy pack from compliance.",
                        "Ensure public statements reflect actual program status."
                    ],
                ))
            
            # Check GDPR/CCPA claims
            if any(term in (cl.claim_text or "").upper() for term in ["GDPR", "CCPA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category,"privacy_compliance_claim", ev)
                discrepancies.append(_build_discrepancy(
                    claim=cl,
                    dtype="privacy_compliance_claim",
                    severity=sev,
                    confidence=conf,
                    why="Privacy compliance should be documented in privacy policy with specific measures.",
                    expected="Privacy policy with GDPR/CCPA-specific rights, DPO contact, or privacy certification.",
                    findings=comp_findings,
                    follow_ups=[
                        "Obtain privacy compliance documentation from legal.",
                        "Clarify public claim with exact scope of GDPR/CCPA coverage."
                    ],
                ))
    sev_counts = {"high":0,"med":0,"low":0}
    for d in discrepancies: sev_counts[d.severity]+=1
    severity_summary = f"H:{sev_counts['high']} • M:{sev_counts['med']} • L:{sev_counts['low']}"
    overall_confidence = min(1.0, 0.5 + 0.1*len(discrepancies))
    return TruthCard(
        url=claims.url,
        company=claims.company,
        severity_summary=severity_summary,
        discrepancies=discrepancies,
        overall_confidence=overall_confidence,
        generated_at=datetime.now(UTC),
    )
