from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


async def fetch_link_meta(url: str) -> tuple[str, str, str]:
    domain = urlparse(url).netloc
    title = ""
    summary = ""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else url
            desc = soup.find("meta", attrs={"name": "description"})
            if desc and desc.get("content"):
                summary = str(desc.get("content")).strip()
    except Exception:
        title = url
        summary = ""
    return title, summary, domain
