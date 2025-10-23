from typing import List
from ..models.sources import AdapterFinding

def confidence_from_findings(findings: List[AdapterFinding]) -> float:
    score = 0.0
    for f in findings:
        if f.status == "confirmed": score += 0.25
        if f.status == "inconsistent": score += 0.2
        if f.status == "not_found": score += 0.15
    return min(1.0, score)
