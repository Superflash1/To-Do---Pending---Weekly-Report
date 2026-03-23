import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _clean_text(value: str | None) -> str:
    return str(value or "").strip()


def _extract_title(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "twitter:title"}),
        soup.find("meta", attrs={"property": "twitter:title"}),
    ]
    for tag in candidates:
        content = _clean_text(tag.get("content") if tag else None)
        if content:
            return content

    if soup.title and soup.title.string:
        title = _clean_text(soup.title.string)
        if title:
            return title

    h1 = soup.find("h1")
    if h1:
        h1_text = _clean_text(h1.get_text(" ", strip=True))
        if h1_text:
            return h1_text

    return ""


def _extract_summary(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"name": "description"}),
        soup.find("meta", attrs={"property": "og:description"}),
        soup.find("meta", attrs={"name": "twitter:description"}),
        soup.find("meta", attrs={"property": "twitter:description"}),
    ]

    for tag in candidates:
        content = _clean_text(tag.get("content") if tag else None)
        if content:
            return content

    return ""


async def fetch_link_meta(url: str) -> tuple[str, str, str]:
    domain = _clean_text(urlparse(url).netloc)
    title = ""
    summary = ""

    try:
        timeout = httpx.Timeout(connect=8.0, read=12.0, write=8.0, pool=8.0)
        async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            content_type = _clean_text(resp.headers.get("content-type")).lower()
            if "html" not in content_type and "xml" not in content_type:
                logger.info(
                    "fetch_link_meta_non_html url=%s domain=%s content_type=%s",
                    url,
                    domain,
                    content_type,
                )
                return url, "", domain

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            title = _extract_title(soup)
            summary = _extract_summary(soup)

    except Exception as exc:
        logger.warning("fetch_link_meta_failed url=%s domain=%s error=%s", url, domain, str(exc))

    final_title = title or url
    return final_title, summary, domain
