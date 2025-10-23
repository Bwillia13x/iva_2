from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

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
    citations: List[Citation]
