def score_severity(claim_category: str, discrepancy_kind: str, evidence_strength: float) -> tuple[str, float]:
    # Simple rubric:
    # - Licensing gaps and false partner claims → High if evidence >= 0.6
    # - SOC2 absent but implied → Medium if evidence >= 0.5
    # - Minor marketing puffery → Low
    if claim_category in ("licensing","partner_bank"):
        if evidence_strength >= 0.6:
            return "high", 0.75
        return "med", 0.55
    if claim_category in ("security","compliance"):
        if evidence_strength >= 0.5:
            return "med", 0.6
        return "low", 0.45
    return "low", 0.5
