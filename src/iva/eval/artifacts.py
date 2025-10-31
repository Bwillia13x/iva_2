from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from ..models.recon import Discrepancy, TruthCard

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except ImportError:  # pragma: no cover - Playwright optional
    sync_playwright = None  # type: ignore


def _slugify(value: str) -> str:
    return "".join([c.lower() if c.isalnum() else "-" for c in value]).strip("-") or "card"


def _discrepancy_summary(discrepancies: Iterable[Discrepancy]) -> list[str]:
    lines: list[str] = []
    for d in discrepancies:
        lines.append(f"{d.type} ({d.severity}) → {d.explanation.verdict}")
        if d.claim_text:
            lines.append(f'  Claim: "{d.claim_text[:120]}"')
        if d.explanation.follow_up_actions:
            lines.append(f"  Next: {d.explanation.follow_up_actions[0]}")
    return lines


def _capture_with_playwright(url: str, annotations: list[str], artifact_dir: Path) -> None:
    if not sync_playwright:
        return
    text_overlay = "\\n".join(annotations[:5]) if annotations else "IVA snapshot"
    screenshot_path = artifact_dir / "page.png"
    dom_path = artifact_dir / "dom.html"
    diff_path = artifact_dir / "dom.diff.txt"
    with sync_playwright() as p:  # pragma: no cover - requires Playwright runner
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        page.evaluate(
            """(notes) => {
                const overlay = document.createElement('div');
                overlay.style.position = 'fixed';
                overlay.style.top = '16px';
                overlay.style.right = '16px';
                overlay.style.zIndex = '2147483647';
                overlay.style.background = 'rgba(8, 47, 73, 0.8)';
                overlay.style.color = '#fff';
                overlay.style.fontFamily = 'monospace';
                overlay.style.padding = '12px';
                overlay.style.borderRadius = '8px';
                overlay.style.maxWidth = '320px';
                overlay.style.whiteSpace = 'pre-wrap';
                overlay.textContent = notes;
                document.body.appendChild(overlay);
            }""",
            text_overlay,
        )
        page.screenshot(path=str(screenshot_path), full_page=True)
        dom_html = page.content()
        browser.close()

    if dom_path.exists():
        previous = dom_path.read_text()
        if previous != dom_html:
            import difflib

            diff = "\n".join(
                difflib.unified_diff(
                    previous.splitlines(),
                    dom_html.splitlines(),
                    fromfile="previous",
                    tofile="current",
                    lineterm="",
                )
            )
            diff_path.write_text(diff or "No diff content", encoding="utf-8")
    dom_path.write_text(dom_html, encoding="utf-8")


def generate_truthcard_artifacts(card: TruthCard, artifact_root: Path | None = None) -> Path:
    root = artifact_root or Path("attached_assets") / "e2e"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    folder = root / f"{stamp}-{_slugify(card.company)}"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "truth_card.json").write_text(card.model_dump_json(indent=2), encoding="utf-8")
    annotations = _discrepancy_summary(card.discrepancies)
    (folder / "summary.txt").write_text("\n".join(annotations), encoding="utf-8")
    _capture_with_playwright(card.url, annotations, folder)
    return folder
