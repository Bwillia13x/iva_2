import json
from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field

FEEDBACK_DIR = Path("data/feedback")
EVENTS_PATH = FEEDBACK_DIR / "events.jsonl"
ADJUSTMENTS_PATH = FEEDBACK_DIR / "rule_adjustments.json"
PROMPT_NOTES_PATH = FEEDBACK_DIR / "prompt_overrides.md"


class AnalystAction(str, Enum):
    CONFIRM = "confirm"
    DISMISS = "dismiss"
    OVERRIDE = "override"
    ESCALATE = "escalate"


class FeedbackEntry(BaseModel):
    card_url: str
    company: str
    discrepancy_type: str
    analyst_action: AnalystAction
    actor: str = "analyst"
    notes: str | None = None
    previous_verdict: str | None = None
    updated_verdict: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeedbackLogger:
    def __init__(self, events_path: Path = EVENTS_PATH):
        self.events_path = events_path
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, entry: FeedbackEntry) -> None:
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json() + "\n")


def load_feedback(events_path: Path = EVENTS_PATH) -> list[FeedbackEntry]:
    if not events_path.exists():
        return []
    entries: list[FeedbackEntry] = []
    with events_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entries.append(FeedbackEntry.model_validate_json(line))
    return entries


def compute_rule_adjustments(entries: Iterable[FeedbackEntry]) -> dict[str, dict[str, float]]:
    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for entry in entries:
        tally[entry.discrepancy_type][entry.analyst_action.value] += 1
    adjustments: dict[str, dict[str, float]] = {}
    for discrepancy_type, counts in tally.items():
        total = sum(counts.values())
        if not total:
            continue
        confirm_bias = (counts.get("confirm", 0) - counts.get("dismiss", 0)) / total
        override_bias = counts.get("override", 0) / total
        adjustments[discrepancy_type] = {
            "threshold_shift": round(confirm_bias * 0.1, 4),
            "confidence_shift": round(override_bias * -0.05, 4),
            "sample_size": total,
        }
    return adjustments


def write_rule_adjustments(
    adjustments: dict[str, dict[str, float]], path: Path = ADJUSTMENTS_PATH
) -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "adjustments": adjustments,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_prompt_overrides(
    entries: Iterable[FeedbackEntry], path: Path = PROMPT_NOTES_PATH
) -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[str]] = defaultdict(list)
    for entry in list(entries)[-20:]:
        note = f"{entry.analyst_action.value}"
        if entry.updated_verdict:
            note += f" → {entry.updated_verdict}"
        if entry.notes:
            note += f" • {entry.notes}"
        grouped[entry.discrepancy_type].append(note)
    lines = [
        "# Prompt Overrides",
        "",
        f"*Last refreshed:* {datetime.now(UTC).isoformat()}",
        "",
    ]
    if not grouped:
        lines.append("_No recent analyst overrides recorded._")
    else:
        for discrepancy_type, notes in grouped.items():
            lines.append(f"## {discrepancy_type}")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def sync_feedback() -> dict[str, dict[str, float]]:
    entries = load_feedback()
    adjustments = compute_rule_adjustments(entries)
    write_rule_adjustments(adjustments)
    write_prompt_overrides(entries)
    return adjustments
