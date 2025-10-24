from typing import List
from ..models.claims import ExtractedClaim, ClaimSet
from ..models.recon import Discrepancy, TruthCard
from .severity import score_severity
from .citations import confidence_from_findings

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
                    sev, conf = score_severity(cl.category,"underlicensed", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="underlicensed_vs_claim",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="Compliance and go-to-market risk; may impact money movement and onboarding.",
                        expected_evidence="NMLS roster export or auditor letter with current state licenses.",
                        findings=findings
                    ))
        if cl.category == "partner_bank":
            bank_findings = adapter_results.get("bank_partners",[]) + adapter_results.get("news",[])
            has_confirmed = any(getattr(f,'status',None)=="confirmed" for f in bank_findings)
            if not has_confirmed:
                ev = confidence_from_findings(bank_findings)
                sev, conf = score_severity(cl.category,"partner_unverified", ev)
                discrepancies.append(Discrepancy(
                    claim_id=cl.id,
                    type="partner_unverified",
                    severity=sev,
                    confidence=conf,
                    why_it_matters="Sponsor bank claims require verification; affects issuing and compliance.",
                    expected_evidence="Bank partner page listing or joint press release.",
                    findings=bank_findings
                ))
        # SECURITY CERTIFICATIONS
        if cl.category == "security":
            sec_findings = adapter_results.get("trust_center",[])
            
            # Check SOC 2 claims
            if "SOC 2" in (cl.claim_text or ""):
                if any(getattr(f,'key',None)=="security_txt" and getattr(f,'status',None)=="not_found" for f in sec_findings):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category,"soc2_unsubstantiated", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="soc2_unsubstantiated",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="Unverified SOC 2 claim can be misleading; request auditor letter or trust center link.",
                        expected_evidence="SOC 2 Type II auditor letter (date, scope) or trust center reference.",
                        findings=sec_findings
                    ))
            
            # Check ISO certifications
            if "ISO 27001" in (cl.claim_text or "") or "ISO" in (cl.claim_text or ""):
                if not any(getattr(f,'key',None)=="iso_cert" and getattr(f,'status',None)=="confirmed" for f in sec_findings):
                    ev = confidence_from_findings(sec_findings)
                    sev, conf = score_severity(cl.category,"iso_unverified", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="iso_unverified",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="ISO certification claims should be verifiable through certificate registries.",
                        expected_evidence="ISO certificate number or listing in certification body database.",
                        findings=sec_findings
                    ))
            
            # Check PCI DSS claims
            if "PCI" in (cl.claim_text or ""):
                ev = confidence_from_findings(sec_findings)
                sev, conf = score_severity(cl.category,"pci_mention", ev)
                discrepancies.append(Discrepancy(
                    claim_id=cl.id,
                    type="pci_requires_verification",
                    severity=sev,
                    confidence=conf,
                    why_it_matters="PCI DSS compliance level should be verified with QSA attestation.",
                    expected_evidence="PCI DSS Attestation of Compliance (AOC) or QSA letter with level and date.",
                    findings=sec_findings
                ))
        
        # MARKETING CLAIMS - Flag unverifiable or exaggerated claims
        if cl.category == "marketing":
            market_findings = adapter_results.get("edgar",[]) + adapter_results.get("news",[])
            
            # Check customer count claims - only flag if NOT confirmed
            if cl.claim_kind and "customer" in cl.claim_kind.lower():
                has_confirmed = any(getattr(f,'status',None)=="confirmed" for f in market_findings)
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category,"customer_count_unverified", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="marketing_metric_unverified",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="Customer counts are often marketing puffery; verify against SEC filings or audited reports.",
                        expected_evidence="SEC 10-K/10-Q user metrics or audited customer count statement.",
                        findings=market_findings
                    ))
            
            # Check transaction volume claims - only flag if NOT confirmed
            if cl.claim_kind and ("volume" in cl.claim_kind.lower() or "transaction" in cl.claim_kind.lower()):
                has_confirmed = any(getattr(f,'status',None)=="confirmed" for f in market_findings)
                if not has_confirmed:
                    ev = confidence_from_findings(market_findings)
                    sev, conf = score_severity(cl.category,"volume_unverified", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="marketing_metric_unverified",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="Transaction volumes should be verified against regulatory filings or audited statements.",
                        expected_evidence="SEC filing with payment volume metrics or press release with audited figures.",
                        findings=market_findings
                    ))
            
            # Check vague claims like "leading", "fastest"
            vague_words = ["leading", "fastest", "best", "#1", "top", "premier"]
            if any(word in (cl.claim_text or "").lower() for word in vague_words):
                ev = confidence_from_findings(market_findings)
                sev, conf = score_severity(cl.category,"vague_marketing", ev)
                discrepancies.append(Discrepancy(
                    claim_id=cl.id,
                    type="vague_marketing_claim",
                    severity=sev,
                    confidence=conf,
                    why_it_matters="Superlative marketing claims ('leading', 'best') are subjective and often unsubstantiated.",
                    expected_evidence="Independent market research, industry report, or specific metric defining 'leading' status.",
                    findings=market_findings
                ))
        
        # REGULATORY CLAIMS
        if cl.category == "regulatory":
            reg_findings = adapter_results.get("cfpb",[]) + adapter_results.get("edgar",[])
            
            # Check SEC registration claims
            if "SEC" in (cl.claim_text or ""):
                sec_filings = [f for f in reg_findings if getattr(f,'key',None)=="edgar_search"]
                if not sec_filings or all(getattr(f,'status',None)!="confirmed" for f in sec_filings):
                    ev = confidence_from_findings(reg_findings)
                    sev, conf = score_severity(cl.category,"sec_unverified", ev)
                    discrepancies.append(Discrepancy(
                        claim_id=cl.id,
                        type="regulatory_claim_unverified",
                        severity=sev,
                        confidence=conf,
                        why_it_matters="SEC registration can be verified through EDGAR; false claims are serious violations.",
                        expected_evidence="CIK number and EDGAR filing history for RIA, BD, or other registration.",
                        findings=reg_findings
                    ))
        
        # COMPLIANCE CLAIMS
        if cl.category == "compliance":
            comp_findings = adapter_results.get("trust_center",[]) + adapter_results.get("edgar",[])
            
            # Check AML/KYC claims
            if any(term in (cl.claim_text or "").upper() for term in ["AML", "KYC", "BSA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category,"aml_program_mention", ev)
                discrepancies.append(Discrepancy(
                    claim_id=cl.id,
                    type="compliance_program_mentioned",
                    severity=sev,
                    confidence=conf,
                    why_it_matters="AML/KYC programs should be documented and verifiable; vague mentions are red flags.",
                    expected_evidence="AML policy document, compliance program description, or regulatory examination results.",
                    findings=comp_findings
                ))
            
            # Check GDPR/CCPA claims
            if any(term in (cl.claim_text or "").upper() for term in ["GDPR", "CCPA"]):
                ev = confidence_from_findings(comp_findings)
                sev, conf = score_severity(cl.category,"privacy_compliance", ev)
                discrepancies.append(Discrepancy(
                    claim_id=cl.id,
                    type="privacy_compliance_claim",
                    severity=sev,
                    confidence=conf,
                    why_it_matters="Privacy compliance should be documented in privacy policy with specific measures.",
                    expected_evidence="Privacy policy with GDPR/CCPA-specific rights, DPO contact, or privacy certification.",
                    findings=comp_findings
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
        overall_confidence=overall_confidence
    )
