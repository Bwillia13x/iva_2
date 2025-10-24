from typing import List, Optional
from pydantic import BaseModel
from .claims import ExtractedClaim
from .sources import AdapterFinding

class Discrepancy(BaseModel):
    claim_id: str
    type: str
    severity: str  # high | med | low
    confidence: float
    why_it_matters: str
    expected_evidence: str
    findings: List[AdapterFinding]
    claim_text: Optional[str] = None

class TruthCard(BaseModel):
    url: str
    company: str
    severity_summary: str
    discrepancies: List[Discrepancy]
    overall_confidence: float
