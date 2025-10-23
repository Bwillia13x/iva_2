from datetime import datetime
from pydantic import BaseModel

class Event(BaseModel):
    ts: datetime
    kind: str
    message: str
    meta: dict | None = None
