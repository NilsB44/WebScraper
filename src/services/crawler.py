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
            wait_until="networkidle",
            delay_before_return_html=10.0,
            magic=True,
            remove_overlay_elements=True,
            page_timeout=90000,  # Increased to 90s
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

    async def fetch_ad_content(self, crawler: AsyncWebCrawler, url: str) -> str | None:
        logger.info(f"📥 Fetching content: {url}")

        # Method 1: Crawl4AI (Browser) for complex sites
        try:
            # Wrap in timeout just in case
            result = await asyncio.wait_for(crawler.arun(url=url, config=self.run_config), timeout=70.0)
            extracted_content = cast(str | None, result.markdown or result.html)

            if extracted_content and len(extracted_content) > 300:
                # Check if we got actual results (not just placeholders)
                placeholders = ["loading...", "wait a moment", "checking your browser"]
                if not any(p in extracted_content.lower() for p in placeholders):
                    return extracted_content[:MAX_CONTENT_LENGTH]
                else:
                    logger.warning(f"   ⚠️ Detected placeholder content for {url}")
        except TimeoutError:
            logger.warning(f"   ⏱️ Timeout fetching {url}")
        except Exception as e:
            logger.warning(f"   ⚠️ Crawler failed for {url}: {e}")

        # Method 2: Requests Fallback
        domains = ["blocket.se", "finn.no", "kleinanzeigen.de", "hifishark.com", "tradera.com"]
        if any(domain in url for domain in domains):
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
        if not href or len(href) < 15:
            return False

        # 1. Mandatory keywords that strongly imply an item page
        item_keywords = [
            "/annons/", "/item/", "/s-anzeige/", "/advert/", "/itm/", "id=",
            "visa_annons", "/bap/forsale/ad.html", "model/", "products/"
        ]
        if any(x in href for x in item_keywords):
            return True

        # 2. Exclude common non-ad pages even if they contain domain names
        exclude_patterns = [
            "/search", "soeg/?", "sok=?", "/annonser/", "/search.html", "?q="
        ]
        if any(x in href for x in exclude_patterns):
            return False

        # 3. Allow absolute URLs that might be external hits from meta-search sites
        # But only if they contain at least one of the item keywords or look like a product page
        # (e.g. they have a long numerical ID or slug)
        known_domains = ["blocket.se", "tradera.com", "hifishark.com", "ebay.de", "kleinanzeigen.de", "dba.dk", "finn.no"]
        if (
            href.startswith("http")
            and any(domain in href for domain in known_domains)
            and any(char.isdigit() for char in href.split("/")[-1])
        ):
            return True

        return False
