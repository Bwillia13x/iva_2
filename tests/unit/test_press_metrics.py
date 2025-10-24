import asyncio
from src.iva.adapters import press_metrics


def test_press_metrics_normalizes_company_names():
    variants_by_company = {
        "Stripe": [
            "Stripe",
            "Stripe Inc",
            "Stripe Inc.",
            "Stripe, Inc.",
            "The Stripe, Inc",
        ],
        "Square": [
            "Square",
            "Square Inc.",
            "The Square, Inc.",
        ],
        "PayPal": [
            "PayPal",
            "PayPal Holdings",
            "PayPal Holdings Inc.",
            "PayPal, Inc.",
        ],
        "SoFi": [
            "SoFi",
            "SoFi Technologies",
            "SoFi Technologies Inc.",
        ],
    }
    for canonical, names in variants_by_company.items():
        for name in names:
            findings = asyncio.run(press_metrics.check_press_metrics(name))
            assert findings, f"Expected metrics for {canonical} variant '{name}'"
            assert any(f.adapter == "press_metrics" and f.status == "confirmed" for f in findings)
