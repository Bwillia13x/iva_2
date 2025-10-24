import json
import re
from datetime import datetime, UTC
from importlib import resources
from ..models.sources import AdapterFinding, Citation
_CORP_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "company",
    "co",
    "ltd",
    "limited",
    "llc",
    "plc",
    "global",
    "technologies",
}

def _normalize_company(name: str) -> str:
    if not name:
        return ""
    norm = name.lower()
    norm = norm.replace("&", " and ")
    norm = re.sub(r"[^a-z0-9\s]", " ", norm)
    tokens = [tok for tok in norm.split() if tok]
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    while tokens and tokens[-1] in _CORP_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)

def _load_dataset() -> list[dict]:
    try:
        with resources.open_text("src.iva.data", "marketing_metrics.json", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError):
        return []

_DATASET = _load_dataset()
_INDEX: dict[str, list[dict]] = {}
for record in _DATASET:
    key = _normalize_company(record.get("company", ""))
    if key:
        _INDEX.setdefault(key, []).append(record)

async def check_press_metrics(company: str) -> list[AdapterFinding]:
    """Return curated press metrics for well-covered fintechs."""
    normalized = _normalize_company(company)
    if not normalized:
        return []
    matched_records = _INDEX.get(normalized, [])
    results: list[AdapterFinding] = []
    for record in matched_records:
        for metric in record.get("metrics", []):
            results.append(AdapterFinding(
                key=metric.get("key","press_metric"),
                value=metric.get("value",""),
                status=metric.get("status","confirmed"),
                adapter="press_metrics",
                observed_at=datetime.now(UTC),
                snippet=metric.get("summary"),
                citations=[Citation(
                    source=metric.get("source_name","Press release"),
                    url=metric.get("source_url",""),
                    query=f"company:{company}",
                    accessed_at=datetime.now(UTC),
                    note=f"As of {metric.get('as_of','unknown')}"
                )]
            ))
    return results
