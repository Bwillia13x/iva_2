import json
from typing import Any, Dict

from openai import OpenAI

from ..config import settings

client = OpenAI(api_key=settings.openai_api_key)


def _use_responses_api(model: str) -> bool:
    """Check if model requires the new Responses API endpoint."""
    return (
        model in ["gpt-5-codex", "gpt-5-thinking"]
        or model.startswith("o1")
        or model.startswith("o3")
        or model.startswith("o4")
    )


def json_call(prompt: str, schema: Dict[str, Any], model: str | None = None) -> Dict[str, Any]:
    """Extract structured JSON using LLM. Supports both Chat Completions and Responses API."""
    model_name = model or settings.openai_model_code

    # For GPT-5 Codex and reasoning models, use Responses API
    if _use_responses_api(model_name):
        try:
            # Use new Responses API for gpt-5-codex, gpt-5-thinking, o-series
            # Note: Responses API doesn't support response_format - request JSON in instructions
            resp = client.responses.create(
                model=model_name,
                instructions=f"You extract fintech claims. Output strict JSON conforming to this schema: {json.dumps(schema)}",
                input=prompt,
                reasoning={"effort": "medium"},
            )
            # Parse output_text which contains the JSON
            content = resp.output_text or ""
            return json.loads(content)
        except AttributeError as e:
            # Responses API not available in this OpenAI SDK version
            raise RuntimeError(
                f"Model '{model_name}' requires OpenAI Responses API, but got error: {e}\n"
                f"Please upgrade: pip install --upgrade openai>=2.0.0 or use a compatible model like 'gpt-4o' or 'gpt-5'"
            )
        except Exception as e:
            # If Responses API fails, provide helpful error
            raise RuntimeError(
                f"Error calling model '{model_name}' with Responses API: {str(e)}\n"
                f"Try using 'gpt-5' or 'gpt-4o' instead, or update OPENAI_MODEL_CODE in .env"
            )
    else:
        # Use standard Chat Completions API for gpt-5, gpt-4o, gpt-4, etc.
        resp = client.chat.completions.create(
            model=model_name,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "schema", "schema": schema, "strict": True},
            },
            messages=[
                {
                    "role": "system",
                    "content": "You extract fintech claims. Output strict JSON conforming to the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = resp.choices[0].message.content or ""
        return json.loads(content)


def text_call(prompt: str, model: str | None = None) -> str:
    """Generate text using LLM. Supports both Chat Completions and Responses API."""
    model_name = model or settings.openai_model_reasoning

    # For GPT-5 reasoning models, use Responses API
    if _use_responses_api(model_name):
        try:
            resp = client.responses.create(
                model=model_name,
                instructions="You are a precise assistant.",
                input=prompt,
                reasoning={"effort": "high"},
            )
            return resp.output_text or ""
        except AttributeError as e:
            # Responses API not available in this OpenAI SDK version
            raise RuntimeError(
                f"Model '{model_name}' requires OpenAI Responses API, but got error: {e}\n"
                f"Please upgrade: pip install --upgrade openai>=2.0.0 or use a compatible model like 'gpt-4o' or 'gpt-5'"
            )
        except Exception as e:
            # If Responses API fails, provide helpful error
            raise RuntimeError(
                f"Error calling model '{model_name}' with Responses API: {str(e)}\n"
                f"Try using 'gpt-5' or 'gpt-4o' instead, or update OPENAI_MODEL_REASONING in .env"
            )
    else:
        # Use standard Chat Completions API
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a precise assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
