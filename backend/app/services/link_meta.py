import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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
    except Exception as exc:
        logger.warning("fetch_link_meta_failed url=%s domain=%s error=%s", url, domain, str(exc))
        title = url
        summary = ""
    return title, summary, domain
