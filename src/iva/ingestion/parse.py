from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text


async def fetch_pdf_text(url: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        pdf = PdfReader(BytesIO(r.content))
        pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n".join(pages)
