# Minimal audit log shim
from datetime import datetime

def log(event: str, meta: dict | None = None):
    ts = datetime.utcnow().isoformat()
    print(f"AUDIT {ts} {event} {meta or {}}")
