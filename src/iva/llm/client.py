import json
import os
from typing import Any, Dict, Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

MODEL_NAME = "gemini-3-flash"

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy initialization of the Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
        base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")
        
        if not api_key or not base_url:
            raise RuntimeError(
                "Gemini AI integration not configured. "
                "Please ensure AI_INTEGRATIONS_GEMINI_API_KEY and AI_INTEGRATIONS_GEMINI_BASE_URL are set."
            )
        
        _client = genai.Client(
            api_key=api_key,
            http_options={
                'api_version': '',
                'base_url': base_url
            }
        )
    return _client


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg 
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower() 
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, 'status') and getattr(exception, 'status', None) == 429)
    )


def json_call(prompt: str, schema: Dict[str, Any], model: str | None = None) -> Dict[str, Any]:
    """Extract structured JSON using Gemini. Returns parsed JSON matching the schema."""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def make_request() -> Dict[str, Any]:
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=f"""You extract fintech claims. Output strict JSON conforming to this schema:
{json.dumps(schema, indent=2)}

{prompt}""",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        content = response.text or "{}"
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    
    return make_request()


def text_call(prompt: str, model: str | None = None) -> str:
    """Generate text using Gemini."""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def make_request() -> str:
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text or ""
    
    return make_request()
