from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
from .cli import _verify
import json

app = FastAPI(title="Iva Truth Meter")
templates = Jinja2Templates(directory="src/iva/web/templates")

class VerifyRequest(BaseModel):
    url: str
    company: str
    jurisdiction: str = "US"
    render_js: bool = False

def sev_emoji(sev: str) -> str:
    return {"high":"🛑","med":"⚠️","low":"ℹ️"}.get(sev, "ℹ️")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": None})

@app.post("/run", response_class=HTMLResponse)
async def run(request: Request,
              url: str = Form(...),
              company: str = Form(...),
              jurisdiction: str = Form("US"),
              render_js: bool = Form(False),
              send_to_slack: bool = Form(False)):
    try:
        card, memo_html = await asyncio.wait_for(
            _verify(url, company, jurisdiction, render_js, emit_slack=send_to_slack),
            timeout=120.0
        )
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": {
                "url": url,
                "company": company,
                "card": card.model_dump(),
                "card_json": json.dumps(card.model_dump(), indent=2, default=str),
                "memo_html": memo_html,
            },
            "sev_emoji": sev_emoji,
            "error": None
        })
    except asyncio.TimeoutError:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": "⏱️ Analysis timed out after 2 minutes. This can happen if the website is very slow to respond or has a lot of content. Please try again or contact support if the issue persists."
        })
    except Exception as e:
        error_msg = str(e)
        user_friendly_error = get_user_friendly_error(error_msg, url)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": user_friendly_error
        })

def sanitize_error_message(error_msg: str) -> str:
    """Remove stack traces and technical details from error messages."""
    lines = error_msg.split('\n')
    sanitized_lines = []
    skip_stack_trace = False
    
    for line in lines:
        # Detect start of stack trace
        if any(pattern in line for pattern in [
            'Traceback (most recent call last):',
            'File "/', 
            'line ', 
            'in <module>',
            'raise ',
            '    at ',
            'File "/usr',
            'site-packages/'
        ]):
            skip_stack_trace = True
            continue
        
        # Skip empty lines during stack trace
        if skip_stack_trace and not line.strip():
            continue
            
        # If we hit a non-stack-trace line, stop skipping
        if skip_stack_trace and line.strip() and not any(c in line for c in ['    ', '\t']):
            skip_stack_trace = False
        
        if not skip_stack_trace and line.strip():
            sanitized_lines.append(line)
    
    # If we filtered everything, return first line only
    if not sanitized_lines and lines:
        # Try to extract just the exception message
        for line in reversed(lines):
            if line.strip() and ':' in line and not any(pattern in line for pattern in ['File "/', 'line ']):
                # This might be the exception type and message
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        return parts[1].strip()
                return line.strip()
        return lines[0].strip() if lines[0].strip() else "Unknown error"
    
    return '\n'.join(sanitized_lines)

def get_user_friendly_error(error_msg: str, url: str) -> str:
    # First sanitize the error to remove stack traces
    error_msg = sanitize_error_message(error_msg)
    error_lower = error_msg.lower()
    
    if "connection" in error_lower or "unreachable" in error_lower or "refused" in error_lower:
        return f"🌐 Unable to connect to {url}. Please check that:<br>• The URL is correct and accessible<br>• The website is currently online<br>• There are no network issues"
    
    if "timeout" in error_lower:
        return f"⏱️ Connection to {url} timed out. The website may be slow or temporarily unavailable. Please try again in a moment."
    
    if "ssl" in error_lower or "certificate" in error_lower:
        return f"🔒 SSL/Certificate error when connecting to {url}. This website may have security certificate issues."
    
    if "dns" in error_lower or "name or service not known" in error_lower or "nodename nor servname" in error_lower:
        return f"🔍 Cannot find website at {url}. Please verify the domain name is correct and exists."
    
    if "404" in error_lower or "not found" in error_lower:
        return f"❌ Page not found at {url}. Please check the URL is correct."
    
    if "403" in error_lower or "forbidden" in error_lower:
        return f"🚫 Access forbidden to {url}. This website may be blocking automated access."
    
    if "api" in error_lower and "key" in error_lower:
        return "🔑 OpenAI API key is not configured or invalid. Please set the OPENAI_API_KEY environment variable."
    
    if "rate limit" in error_lower:
        return "⚡ API rate limit exceeded. Please wait a moment and try again."
    
    # Preserve multiline formatting with HTML breaks
    if '\n' in error_msg:
        error_msg = error_msg.replace('\n', '<br>')
    
    if len(error_msg) > 300:
        return f"❌ An error occurred during analysis:<br>{error_msg[:300]}...<br><br>Please try again or contact support if the issue persists."
    
    return f"❌ An error occurred: {error_msg}"

@app.post("/verify")
async def verify(req: VerifyRequest):
    await _verify(req.url, req.company, req.jurisdiction, req.render_js)
    return {"status":"ok"}
