import asyncio
from .cli import _verify

async def run_periodic(url: str, company: str, interval_sec: int = 3600):
    while True:
        try:
            await _verify(url, company, "US", False)
        except Exception as e:
            print(f"scheduler error: {e}")
        await asyncio.sleep(interval_sec)
