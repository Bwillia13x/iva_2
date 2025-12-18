import asyncio
import json
import time
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .alerts.monitor import AlertManager
from .alerts.notifications import send_alert
from .cli import _verify
from .export.pdf import generate_pdf

app = FastAPI(title="Iva Truth Meter")
templates = Jinja2Templates(directory="src/iva/web/templates")


class VerifyRequest(BaseModel):
    url: str
    company: str
    jurisdiction: str = "US"
    render_js: bool = False
    ticker: Optional[str] = None


def sev_emoji(sev: str) -> str:
    return {"high": "🛑", "med": "⚠️", "low": "ℹ️"}.get(sev, "ℹ️")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "result": None, "error": None}
    )


@app.post("/run", response_class=HTMLResponse)
async def run(
    request: Request,
    url: str = Form(...),
    company: str = Form(...),
    jurisdiction: str = Form("US"),
    ticker: str = Form(""),
    render_js: bool = Form(False),
    send_to_slack: bool = Form(False),
):
    try:
        start_time = time.time()
        card, memo_html = await asyncio.wait_for(
            _verify(
                url,
                company,
                jurisdiction,
                render_js,
                emit_slack=send_to_slack,
                ticker=ticker or None,
            ),
            timeout=120.0,
        )
        elapsed_time = time.time() - start_time
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {
                    "url": url,
                    "company": company,
                    "card": card.model_dump(),
                    "card_json": json.dumps(card.model_dump(), indent=2, default=str),
                    "memo_html": memo_html,
                    "analysis_time": round(elapsed_time, 1),
                },
                "sev_emoji": sev_emoji,
                "error": None,
            },
        )
    except asyncio.TimeoutError:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": "⏱️ Analysis timed out after 2 minutes. This can happen if the website is very slow to respond or has a lot of content. Please try again or contact support if the issue persists.",
            },
        )
    except Exception as e:
        error_msg = str(e)
        user_friendly_error = get_user_friendly_error(error_msg, url)
        return templates.TemplateResponse(
            "index.html", {"request": request, "result": None, "error": user_friendly_error}
        )


def sanitize_error_message(error_msg: str) -> str:
    """Remove stack traces and technical details from error messages."""
    lines = error_msg.split("\n")
    sanitized_lines = []
    skip_stack_trace = False

    for line in lines:
        # Detect start of stack trace
        if any(
            pattern in line
            for pattern in [
                "Traceback (most recent call last):",
                'File "/',
                "line ",
                "in <module>",
                "raise ",
                "    at ",
                'File "/usr',
                "site-packages/",
            ]
        ):
            skip_stack_trace = True
            continue

        # Skip empty lines during stack trace
        if skip_stack_trace and not line.strip():
            continue

        # If we hit a non-stack-trace line, stop skipping
        if skip_stack_trace and line.strip() and not any(c in line for c in ["    ", "\t"]):
            skip_stack_trace = False

        if not skip_stack_trace and line.strip():
            sanitized_lines.append(line)

    # If we filtered everything, return first line only
    if not sanitized_lines and lines:
        # Try to extract just the exception message
        for line in reversed(lines):
            if (
                line.strip()
                and ":" in line
                and not any(pattern in line for pattern in ['File "/', "line "])
            ):
                # This might be the exception type and message
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
                return line.strip()
        return lines[0].strip() if lines[0].strip() else "Unknown error"

    return "\n".join(sanitized_lines)


def get_user_friendly_error(error_msg: str, url: str) -> str:
    # First sanitize the error to remove stack traces
    error_msg = sanitize_error_message(error_msg)
    error_lower = error_msg.lower()

    if "connection" in error_lower or "unreachable" in error_lower or "refused" in error_lower:
        return f"🌐 Unable to connect to {url}. Please check that:\n• The URL is correct and accessible\n• The website is currently online\n• There are no network issues"

    if "timeout" in error_lower:
        return f"⏱️ Connection to {url} timed out. The website may be slow or temporarily unavailable. Please try again in a moment."

    if "ssl" in error_lower or "certificate" in error_lower:
        return f"🔒 SSL/Certificate error when connecting to {url}. This website may have security certificate issues."

    if (
        "dns" in error_lower
        or "name or service not known" in error_lower
        or "nodename nor servname" in error_lower
    ):
        return (
            f"🔍 Cannot find website at {url}. Please verify the domain name is correct and exists."
        )

    if "404" in error_lower or "not found" in error_lower:
        return f"❌ Page not found at {url}. Please check the URL is correct."

    if "403" in error_lower or "forbidden" in error_lower:
        return f"🚫 Access forbidden to {url}. This website may be blocking automated access."

    if "api" in error_lower and "key" in error_lower:
        return "🔑 AI API key is not configured or invalid. Please check your API configuration."

    if "rate limit" in error_lower:
        return "⚡ API rate limit exceeded. Please wait a moment and try again."

    if (
        "playwright" in error_lower
        or "browsertype.launch" in error_lower
        or "missing dependencies to run browsers" in error_lower
    ):
        return "🌐 JavaScript rendering is not available in this environment.\n\nThe 'Render JS' option requires browser dependencies that aren't installed. Please uncheck the 'Render JS' checkbox and try again - standard HTML fetching works well for most websites and still extracts comprehensive claims."

    # Keep multiline formatting with plain text newlines (CSS will handle display)
    if len(error_msg) > 300:
        return f"❌ An error occurred during analysis:\n{error_msg[:300]}...\n\nPlease try again or contact support if the issue persists."

    return f"❌ An error occurred: {error_msg}"


@app.post("/verify")
async def verify(req: VerifyRequest):
    await _verify(req.url, req.company, req.jurisdiction, req.render_js)
    return {"status": "ok"}


# Public API endpoints for programmatic access


class VerifyAPIRequest(BaseModel):
    """Request model for API verification"""

    url: str
    company: str
    jurisdiction: str = "US"
    ticker: Optional[str] = None
    render_js: bool = False
    generate_alerts: bool = True


@app.post("/api/v1/verify", response_model=dict)
async def api_verify(req: VerifyAPIRequest):
    """
    Verify company claims against authoritative sources.

    Returns a truth card with discrepancies and verification results.
    """
    try:
        card, memo_html = await asyncio.wait_for(
            _verify(
                req.url,
                req.company,
                req.jurisdiction,
                req.render_js,
                emit_slack=False,
                ticker=req.ticker,
            ),
            timeout=120.0,
        )

        # Generate alerts if requested
        alerts = []
        if req.generate_alerts:
            alert_manager = AlertManager()
            alerts = alert_manager.process_truth_card(card)
            # Send alerts asynchronously
            for alert in alerts:
                if alert.severity.value in ["critical", "high"]:
                    await send_alert(alert)

        return {
            "status": "success",
            "truth_card": card.model_dump(),
            "memo_html": memo_html,
            "alerts_generated": len(alerts),
            "alerts": [a.model_dump() for a in alerts],
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Analysis timed out after 2 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/alerts/{company}", response_model=dict)
async def api_get_alerts(
    company: str,
    limit: int = Query(100, description="Maximum number of alerts to return"),
    unacknowledged_only: bool = Query(False, description="Return only unacknowledged alerts"),
):
    """
    Get alerts for a company.

    Returns list of alerts sorted by generation time (most recent first).
    """
    alert_manager = AlertManager()
    alerts = alert_manager.load_alerts(
        company, limit=limit, unacknowledged_only=unacknowledged_only
    )

    return {
        "status": "success",
        "company": company,
        "count": len(alerts),
        "alerts": [a.model_dump() for a in alerts],
    }


@app.post("/api/v1/alerts/{company}/{alert_id}/acknowledge", response_model=dict)
async def api_acknowledge_alert(company: str, alert_id: str):
    """
    Acknowledge an alert.

    Marks an alert as acknowledged to prevent duplicate notifications.
    """
    alert_manager = AlertManager()
    success = alert_manager.acknowledge_alert(company, alert_id)

    if success:
        return {"status": "success", "message": f"Alert {alert_id} acknowledged"}

    raise HTTPException(
        status_code=404, detail=f"Alert {alert_id} not found or already acknowledged"
    )


@app.get("/api/v1/truth-card/{company}/pdf")
async def api_export_pdf(company: str, url: str = Query(..., description="Company website URL")):
    """
    Export truth card as PDF.

    Generates a PDF report from the most recent truth card for a company.
    """
    # Get latest truth card (would need to store/retrieve truth cards)
    # For MVP, generate on-demand
    try:
        card, _ = await asyncio.wait_for(
            _verify(url, company, "US", False, emit_slack=False), timeout=120.0
        )

        pdf_bytes = generate_pdf(card)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="iva_truth_card_{company.replace(" ", "_")}.pdf"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def api_health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Iva Truth Meter"}
