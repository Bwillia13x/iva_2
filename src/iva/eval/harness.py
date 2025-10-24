import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Sequence, Any
from ..models.recon import TruthCard

class EvaluationTier(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"

@dataclass
class EvaluationReport:
    tier: EvaluationTier
    metrics: dict[str, float]
    failures: list[str]
    drift_alerts: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "metrics": self.metrics,
            "failures": self.failures,
            "drift_alerts": self.drift_alerts,
        }

def load_golden():
    p = pathlib.Path("src/iva/eval/datasets/golden.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def _ensure_truth_card(card: TruthCard | dict) -> TruthCard:
    if isinstance(card, TruthCard):
        return card
    data = dict(card)
    data.setdefault("generated_at", datetime.now(UTC))
    return TruthCard(**data)

def _ensure_tier(tier: str | EvaluationTier) -> EvaluationTier:
    if isinstance(tier, EvaluationTier):
        return tier
    try:
        return EvaluationTier(tier)
    except ValueError as exc:
        raise ValueError(f"Unknown evaluation tier: {tier}") from exc

def evaluate(pred_cards: Sequence[TruthCard | dict], golden: Sequence[dict], tier: str | EvaluationTier = EvaluationTier.UNIT) -> EvaluationReport:
    target_tier = _ensure_tier(tier)
    metrics: dict[str, float] = {}
    failures: list[str] = []
    drift_alerts: list[str] = []

    golden_by_url = {g["url"]: g for g in golden}
    expected_total = 0
    matched_expected = 0
    bundle_checks = 0
    bundle_complete = 0
    unexpected_high = 0

    for raw_card in pred_cards:
        card = _ensure_truth_card(raw_card)
        expected_entry = golden_by_url.get(card.url)
        if not expected_entry:
            failures.append(f"{card.url} missing from golden dataset")
            continue

        expected_truth = expected_entry.get("expected_truth_card", {})
        expected_discrepancies = expected_truth.get("expected_discrepancies", [])
        expected_index = {d["type"]: d for d in expected_discrepancies}
        expected_total += len(expected_discrepancies)
        predicted_map = {d.type: d for d in card.discrepancies}

        if target_tier in (EvaluationTier.UNIT, EvaluationTier.INTEGRATION, EvaluationTier.REGRESSION):
            for discrepancy in card.discrepancies:
                bundle_checks += 1
                if discrepancy.explanation.supporting_evidence and discrepancy.provenance:
                    bundle_complete += 1
                else:
                    failures.append(f"{card.url}::{discrepancy.type} missing structured bundle fields")

        for expected_disc in expected_discrepancies:
            dtype = expected_disc["type"]
            predicted = predicted_map.get(dtype)
            if not predicted:
                failures.append(f"{card.url} missing expected discrepancy {dtype}")
                continue
            matched_expected += 1
            if target_tier in (EvaluationTier.INTEGRATION, EvaluationTier.REGRESSION):
                expected_sev = expected_disc.get("severity")
                if expected_sev and predicted.severity != expected_sev:
                    failures.append(f"{card.url}::{dtype} severity {predicted.severity} != expected {expected_sev}")
            if target_tier is EvaluationTier.REGRESSION:
                expected_verdict = expected_disc.get("verdict")
                if expected_verdict and predicted.explanation.verdict != expected_verdict:
                    failures.append(f"{card.url}::{dtype} verdict {predicted.explanation.verdict} != expected {expected_verdict}")

        expected_types = set(expected_index.keys())
        for discrepancy in card.discrepancies:
            if discrepancy.severity == "high" and discrepancy.type not in expected_types:
                unexpected_high += 1

        if target_tier is EvaluationTier.REGRESSION:
            expected_conf_range = expected_truth.get("confidence_range")
            if expected_conf_range and len(expected_conf_range) == 2:
                low, high = expected_conf_range
                if not (low <= card.overall_confidence <= high):
                    drift_alerts.append(
                        f"{card.url} confidence {card.overall_confidence:.2f} outside expected range [{low}, {high}]"
                    )

    metrics["cards_evaluated"] = float(len(pred_cards))
    metrics["expected_discrepancy_recall"] = matched_expected / expected_total if expected_total else 1.0
    metrics["unexpected_high_discrepancies"] = float(unexpected_high)
    metrics["bundle_completeness"] = bundle_complete / bundle_checks if bundle_checks else 1.0
    metrics["failures"] = float(len(failures))
    metrics["drift_alerts"] = float(len(drift_alerts))

    return EvaluationReport(
        tier=target_tier,
        metrics=metrics,
        failures=failures,
        drift_alerts=drift_alerts,
    )
