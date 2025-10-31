# Placeholder for pgvector integration
from typing import Optional

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def embed(text: str) -> Optional[list[float]]:
    if np is None:
        return None
    # toy embedding: length & vowels count
    v = sum(ch.lower() in "aeiou" for ch in text)
    return [len(text) % 1000 / 1000.0, v % 10 / 10.0]
