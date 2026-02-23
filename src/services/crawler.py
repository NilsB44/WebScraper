import asyncio
import logging
from typing import cast
from urllib.parse import urljoin

import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig  # type: ignore

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 150000


class ContentFetcher:
    def __init__(self, headless: bool = True):
        self.browser_config = BrowserConfig(
            headless=headless,
            extra_args=["--disable-blink-features=AutomationControlled"],
        )
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="domcontentloaded",  # More resilient for some sites
            delay_before_return_html=5.0,
            magic=True,
        )

    async def fetch_ad_content(self, crawler: AsyncWebCrawler, url: str) -> str | None:
        logger.info(f"📥 Fetching content: {url}")

        await asyncio.sleep(1)

        try:
            # Wrap in timeout just in case
            result = await asyncio.wait_for(crawler.arun(url=url, config=self.run_config), timeout=45.0)
            extracted_content = cast(str | None, result.markdown or result.html)

            if extracted_content and len(extracted_content) > 300:
                return extracted_content[:MAX_CONTENT_LENGTH]
        except TimeoutError:
            logger.warning(f"   ⏱️ Timeout fetching {url}")
        except Exception as e:
            logger.warning(f"   ⚠️ Crawler failed for {url}: {e}")

        # Method 2: Requests Fallback
        if any(domain in url for domain in ["blocket.se", "finn.no", "kleinanzeigen.de"]):
            logger.info("   ⚠️ Trying requests fallback...")
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
                return resp.text[:30000]
        except Exception as e:
            logger.error(f"   ❌ Fallback failed: {e}")
        return None

    @staticmethod
    def fix_relative_url(base_url: str, href: str) -> str:
        if not href:
            return ""
        return urljoin(base_url, href)

    @staticmethod
    def is_valid_ad_link(href: str) -> bool:
        if len(href) < 15:
            return False
        keywords = ["/annons/", "/item/", "/s-anzeige/", "/advert/", "/itm/", "id="]
        return any(x in href for x in keywords)
