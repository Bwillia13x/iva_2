from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

ClaimCategory = Literal[
    "licensing",
    "regulatory",
    "partner_bank",
    "security",
    "compliance",
    "marketing",
    "financial_performance",
    "market_position",
    "business_metrics",
    "forward_looking",
    "governance",
    "litigation",
    "intellectual_property",
    "material_events"
]
Jurisdiction = Literal["US","CA","EU","UK","OTHER"]

class SourceRef(BaseModel):
    name: str
    url: str
    accessed_at: datetime

class ExtractedClaim(BaseModel):
    id: str
    category: ClaimCategory
    claim_text: str
    entity: Optional[str] = None
    jurisdiction: Optional[Jurisdiction] = None
    claim_kind: Optional[str] = None
    values: Optional[List[str]] = None
    effective_date: Optional[str] = None
    page_context: Optional[str] = None
    confidence: float = Field(ge=0, le=1, default=0.6)
    citations: List[SourceRef] = Field(default_factory=list)

class ClaimSet(BaseModel):
    url: str
    company: str
    extracted_at: datetime
    claims: List[ExtractedClaim]
