import asyncio
import logging
from typing import cast
from urllib.parse import urljoin

import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig  # type: ignore

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 20000


class ContentFetcher:
    def __init__(self, headless: bool = True):
        self.browser_config = BrowserConfig(
            headless=headless,
            extra_args=["--disable-blink-features=AutomationControlled"],
        )
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            delay_before_return_html=8.0,
            magic=True,
        )

    async def fetch_ad_content(self, crawler: AsyncWebCrawler, url: str) -> str | None:
        logger.info(f"📥 Fetching content: {url}")

        # Use asyncio.sleep instead of time.sleep in an async function
        await asyncio.sleep(1)

        # Method 1: Crawl4AI
        try:
            result = await crawler.arun(url=url, config=self.run_config)
            # Use meaningful variable names
            extracted_content = cast(str | None, result.markdown or result.html)

            if extracted_content and len(extracted_content) > 500:
                # Use named constant instead of magic number
                return extracted_content[:MAX_CONTENT_LENGTH]
        except Exception as e:
            logger.warning(f"⚠️ Crawler failed for {url}: {e}")

        # Method 2: Requests Fallback (Specific Logic)
        # Using a specialized header set mimicking a real browser
        if any(domain in url for domain in ["blocket.se", "finn.no"]):
            logger.info("   ⚠️ Trying requests fallback for Schibsted site...")
            return self._fetch_with_requests(url)

        return None

    def _fetch_with_requests(self, url: str) -> str | None:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200 and len(resp.text) > 500:
                logger.info(f"   ✅ Requests fallback worked ({len(resp.text)} chars).")
                return resp.text[:30000]
        except Exception as e:
            logger.error(f"   ❌ Fallback failed: {e}")
        return None

    @staticmethod
    def fix_relative_url(base_url: str, href: str) -> str:
        """Correctly joins relative URLs."""
        if not href:
            return ""
        return urljoin(base_url, href)

    @staticmethod
    def is_valid_ad_link(href: str) -> bool:
        """Filters obviously bad links."""
        if len(href) < 20:
            return False

        # Common patterns for ad detail pages
        keywords = ["/annons/", "/item/", "/s-anzeige/", "/advert/", "/itm/", "id="]
        return any(x in href for x in keywords)
