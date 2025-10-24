import asyncio
from src.iva.adapters import press_metrics


def test_press_metrics_normalizes_company_names():
    names = [
        "Stripe",
        "Stripe Inc",
        "Stripe Inc.",
        "Stripe, Inc.",
        "The Stripe, Inc",
    ]
    for name in names:
        findings = asyncio.run(press_metrics.check_press_metrics(name))
        assert findings, f"Expected metrics for {name}"
        assert any(f.adapter == "press_metrics" and f.status == "confirmed" for f in findings)
