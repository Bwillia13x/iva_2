import os, json
from typing import Any, Dict
from pydantic import BaseModel
from openai import OpenAI
from ..config import settings

client = OpenAI(api_key=settings.openai_api_key)

def json_call(prompt: str, schema: Dict[str, Any], model: str | None = None) -> Dict[str, Any]:
    model = model or settings.openai_model_code
    resp = client.chat.completions.create(
        model=model,
        response_format={"type":"json_schema","json_schema":{"name":"schema","schema":schema,"strict":True}},
        messages=[
            {"role":"system","content":"You extract fintech claims. Output strict JSON conforming to the schema."},
            {"role":"user","content":prompt}
        ],
        temperature=0.1
    )
    return json.loads(resp.choices[0].message.content)

def text_call(prompt: str, model: str | None = None) -> str:
    model = model or settings.openai_model_reasoning
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"You are a precise assistant."},{"role":"user","content":prompt}],
        temperature=0.2
    )
    return resp.choices[0].message.content
