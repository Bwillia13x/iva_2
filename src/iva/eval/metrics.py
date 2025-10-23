def precision_at_k(pred: list[int], truth: list[int], k: int = 5) -> float:
    if not pred:
        return 0.0
    p = pred[:k]
    tset = set(truth)
    hits = sum(1 for x in p if x in tset)
    return hits / min(k, len(pred))
