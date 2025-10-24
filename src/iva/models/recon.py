from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .sources import AdapterFinding

class EvidencePointer(BaseModel):
    adapter: str
    finding_key: str
    summary: str
    citation_urls: List[str] = Field(default_factory=list)

class ExplanationBundle(BaseModel):
    verdict: str
    supporting_evidence: List[EvidencePointer]
    confidence: float
    follow_up_actions: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

class FindingProvenance(BaseModel):
    adapter: str
    finding_key: str
    observed_at: datetime
    snippet: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)

class Discrepancy(BaseModel):
    claim_id: str
    type: str
    severity: str  # high | med | low
    confidence: float
    why_it_matters: str
    expected_evidence: str
    findings: List[AdapterFinding]
    claim_text: Optional[str] = None
    explanation: ExplanationBundle
    provenance: List[FindingProvenance] = Field(default_factory=list)
    related_claims: List[str] = Field(default_factory=list)
    related_claim_texts: List[str] = Field(default_factory=list)

class TruthCard(BaseModel):
    url: str
    company: str
    severity_summary: str
    discrepancies: List[Discrepancy]
    overall_confidence: float
    generated_at: datetime
