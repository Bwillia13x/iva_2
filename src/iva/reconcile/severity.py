import json
from pathlib import Path

def _load_rule_adjustments() -> dict[str, dict]:
    path = Path("data/feedback/rule_adjustments.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return payload.get("adjustments", {})

_ADJUSTMENTS = _load_rule_adjustments()

def _threshold_for(kind: str, default: float) -> float:
    shift = _ADJUSTMENTS.get(kind, {}).get("threshold_shift", 0.0)
    return max(0.0, min(1.0, default + shift))

def _confidence_bump(kind: str, base: float) -> float:
    bump = _ADJUSTMENTS.get(kind, {}).get("confidence_shift", 0.0)
    return max(0.0, min(1.0, base + bump))

def score_severity(claim_category: str, discrepancy_kind: str, evidence_strength: float) -> tuple[str, float]:
    """
    Determine severity bucket and confidence given evidence strength.
    Analyst feedback can adjust thresholds via data/feedback/rule_adjustments.json.
    """
    if claim_category in ("licensing","partner_bank"):
        high_threshold = _threshold_for(discrepancy_kind, 0.6)
        if evidence_strength >= high_threshold:
            return "high", _confidence_bump(discrepancy_kind, 0.75)
        return "med", _confidence_bump(discrepancy_kind, 0.55)
    if claim_category in ("security","compliance"):
        med_threshold = _threshold_for(discrepancy_kind, 0.5)
        if evidence_strength >= med_threshold:
            return "med", _confidence_bump(discrepancy_kind, 0.6)
        return "low", _confidence_bump(discrepancy_kind, 0.45)
    low_conf = _confidence_bump(discrepancy_kind, 0.5)
    return "low", low_conf
