import json, pathlib, statistics
from ..reconcile.severity import score_severity

def load_golden():
    p = pathlib.Path("src/iva/eval/datasets/golden.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def evaluate(pred_cards, golden):
    # Placeholder: compute basic coverage of high-sev flags when expected
    # Extend with precision@K, severity accuracy, latency tracking
    return {"dummy_metric": 1.0}
