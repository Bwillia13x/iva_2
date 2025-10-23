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
        card, memo_html = await _verify(url, company, jurisdiction, render_js, emit_slack=send_to_slack)
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
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": str(e)
        })

@app.post("/verify")
async def verify(req: VerifyRequest):
    await _verify(req.url, req.company, req.jurisdiction, req.render_js)
    return {"status":"ok"}
