import httpx
from playwright.async_api import async_playwright

from ..config import settings


async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=settings.request_timeout, headers={"User-Agent": settings.user_agent}
    ) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.text


async def fetch_rendered(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=settings.user_agent)
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        await browser.close()
        return content
