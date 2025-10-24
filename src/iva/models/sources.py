from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Citation(BaseModel):
    source: str
    url: str
    query: str
    accessed_at: datetime
    note: Optional[str] = None

class AdapterFinding(BaseModel):
    key: str
    value: str
    status: str  # "confirmed" | "not_found" | "inconsistent" | "unknown"
    adapter: str
    observed_at: datetime
    snippet: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
