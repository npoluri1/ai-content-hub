import logging
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..core.models import ContentItem

logger = logging.getLogger(__name__)

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    logger.debug("trafilatura not installed")

try:
    from readability import Document as ReadabilityDocument
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False
    logger.debug("readability-lxml not installed")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class FullTextExtractor:
    def __init__(self, timeout: int = 30, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries

    def extract(self, url: str) -> dict:
        result = self._extract_trafilatura(url)
        if result.get("content"):
            logger.debug(f"trafilatura succeeded for {url}")
            return result

        result = self._extract_readability(url)
        if result.get("content"):
            logger.debug(f"readability succeeded for {url}")
            return result

        result = self._extract_soup(url)
        if result.get("content"):
            logger.debug(f"beautifulsoup succeeded for {url}")
            return result

        return {"url": url, "title": "", "content": "", "text": "", "author": "", "date": "", "site_name": "", "image": "", "description": ""}

    async def extract_async(self, url: str) -> dict:
        return self.extract(url)

    def extract_batch(self, urls: list[str], max_concurrent: int = 5) -> list[dict]:
        import concurrent.futures
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {executor.submit(self.extract, url): url for url in urls}
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    url = futures[future]
                    logger.error(f"Batch extract failed for {url}: {e}")
                    results.append({"url": url, "title": "", "content": "", "text": "", "author": "", "date": "", "site_name": "", "image": "", "description": ""})
        return results

    def extract_and_enrich(self, item: ContentItem) -> ContentItem:
        if not item.url:
            return item
        data = self.extract(item.url)
        if data.get("title") and not item.title:
            item.title = data["title"]
        if data.get("content"):
            item.content = data["content"]
        if data.get("text") and not item.content_cleaned:
            item.content_cleaned = data["text"]
        if data.get("author_name") and not item.author_name:
            item.author_name = data["author_name"]
        if data.get("image") and not item.image_urls:
            item.image_urls = [data["image"]]
        if data.get("metadata"):
            item.metadata.update(data["metadata"])
        return item

    def _fetch_html(self, url: str) -> Optional[str]:
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(url, headers=DEFAULT_HEADERS)
                    resp.raise_for_status()
                    return resp.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    import time as t
                    t.sleep(2 ** (attempt + 1))
                    continue
                logger.warning(f"HTTP error fetching {url}: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch {url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries:
                    import time as t
                    t.sleep(1)
                else:
                    return None
        return None

    def _extract_trafilatura(self, url: str) -> dict:
        if not HAS_TRAFILATURA:
            return {}
        try:
            html = self._fetch_html(url)
            if not html:
                return {}
            result = trafilatura.extract(
                html,
                output_format="json",
                include_comments=False,
                include_tables=False,
                include_images=False,
                with_metadata=True,
            )
            if result:
                import json
                data = json.loads(result)
                return {
                    "url": url,
                    "title": data.get("title", ""),
                    "content": data.get("raw_text", ""),
                    "text": data.get("raw_text", ""),
                    "author": data.get("author", ""),
                    "date": data.get("date", ""),
                    "site_name": data.get("sitename", ""),
                    "image": data.get("image", ""),
                    "description": data.get("description", ""),
                }
        except Exception as e:
            logger.debug(f"trafilatura error for {url}: {e}")
        return {}

    def _extract_readability(self, url: str) -> dict:
        if not HAS_READABILITY:
            return {}
        try:
            html = self._fetch_html(url)
            if not html:
                return {}
            doc = ReadabilityDocument(html)
            content_html = doc.summary()
            title = doc.title() or ""
            soup = BeautifulSoup(content_html, "lxml")
            text = soup.get_text(separator="\n", strip=True)
            return {
                "url": url,
                "title": title,
                "content": content_html,
                "text": text,
                "author": "",
                "date": "",
                "site_name": "",
                "image": "",
                "description": "",
            }
        except Exception as e:
            logger.debug(f"readability error for {url}: {e}")
        return {}

    def _extract_soup(self, url: str) -> dict:
        try:
            html = self._fetch_html(url)
            if not html:
                return {}
            soup = BeautifulSoup(html, "lxml")
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            text = "\n".join(line for line in text.splitlines() if len(line.strip()) > 30)
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"]
            image = ""
            meta_image = soup.find("meta", attrs={"property": "og:image"})
            if meta_image and meta_image.get("content"):
                image = meta_image["content"]
            site_name = ""
            meta_site = soup.find("meta", attrs={"property": "og:site_name"})
            if meta_site and meta_site.get("content"):
                site_name = meta_site["content"]
            return {
                "url": url,
                "title": title,
                "content": text,
                "text": text,
                "author": "",
                "date": "",
                "site_name": site_name,
                "image": image,
                "description": description,
            }
        except Exception as e:
            logger.debug(f"soup extraction error for {url}: {e}")
        return {}
