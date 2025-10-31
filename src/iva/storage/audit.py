# Minimal audit log shim
from datetime import UTC, datetime


def log(event: str, meta: dict | None = None):
    ts = datetime.now(UTC).isoformat()
    print(f"AUDIT {ts} {event} {meta or {}}")
