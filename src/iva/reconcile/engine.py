from typing import List
from ..models.claims import ExtractedClaim, ClaimSet
from ..models.recon import Discrepancy, TruthCard
from .severity import score_severity
from .citations import confidence_from_findings

def reconcile(claims: ClaimSet, adapter_results: dict[str, list]) -> TruthCard:
    discrepancies: List[Discrepancy] = []
    for cl in claims.claims:
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
        if cl.category == "security" and "SOC 2" in (cl.claim_text or ""):
            sec_findings = adapter_results.get("trust_center",[])
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
