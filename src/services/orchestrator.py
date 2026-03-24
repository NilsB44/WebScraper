import logging
from typing import Any
from crawl4ai import AsyncWebCrawler  # type: ignore

from src.models import ScrapeTask, SearchPageSource
from src.services.analysis import GeminiAnalyzer
from src.services.crawler import ContentFetcher
from src.services.notification import NotificationService
from src.services.presenter import ResultsPresenter

logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    def __init__(
        self,
        analyzer: GeminiAnalyzer,
        content_fetcher: ContentFetcher,
        notification_service: NotificationService,
        presenter: ResultsPresenter,
        target_sites: list[str]
    ):
        self.analyzer = analyzer
        self.content_fetcher = content_fetcher
        self.notification_service = notification_service
        self.presenter = presenter
        self.target_sites = target_sites

    async def run_task(self, task: ScrapeTask, crawler: AsyncWebCrawler, seen_urls: list[str]) -> list[str]:
        logger.info(f"\n⚡ Starting Task: {task.name}")
        self.notification_service.notify_start(task.name)

        # A. Generate Queries / Direct URLs
        if task.search_query.startswith("http"):
            logger.info(f"   🔗 Direct URL detected: {task.search_query}")
            all_search_urls = [SearchPageSource(site_name="Direct", search_url=task.search_query)]
        else:
            queries = [task.search_query]
            if task.fuzzy_search:
                variations = await self.analyzer.generate_query_variations(task.search_query)
                queries.extend([v for v in variations if v not in queries])

            logger.info(f"   🔎 Searching for queries: {', '.join(queries)}")

            all_search_urls = []
            for q in queries:
                urls = await self.analyzer.get_search_urls(q, self.target_sites)
                all_search_urls.extend(urls)

        ads_to_analyze: list[dict[str, str]] = []

        # B. Agentic Search Page Analysis
        for source in all_search_urls:
            logger.info(f"   🌐 Checking: {source.search_url}")

            list_content = await self.content_fetcher.fetch_ad_content(crawler, source.search_url)
            if not list_content:
                continue

            candidates = await self.analyzer.analyze_search_page(list_content, task)

            if not candidates:
                logger.info("   ℹ️ No candidates found on this page.")
                continue

            logger.info(f"   ✅ Agent selected {len(candidates)} candidates.")

            # C. Deep Dive
            for cand in candidates:
                full_url = self.content_fetcher.fix_relative_url(source.search_url, cand.url)
                
                if full_url in seen_urls:
                    continue

                if not self.content_fetcher.is_valid_ad_link(full_url):
                    continue

                logger.info(f"      🕵️ Deep diving: {cand.title} ({cand.price})")

                ad_content = await self.content_fetcher.fetch_ad_content(crawler, full_url)
                if ad_content:
                    ads_to_analyze.append({"site": source.site_name, "url": full_url, "content": ad_content})
                    seen_urls.append(full_url)

        # D. Batch Verify
        if ads_to_analyze:
            item_label = task.name if task.search_query.startswith("http") else task.search_query
            logger.info(f"   🧠 Verifying {len(ads_to_analyze)} candidates for {item_label}...")
            results = await self.analyzer.analyze_batch(item_label, ads_to_analyze)

            confirmed_hits = []
            if results:
                for res in results:
                    if res.found_item:
                        logger.info(f"      🎉 MATCH! {res.item_name} - {res.price}")
                        self.notification_service.notify_match(res.item_name, res.price, res.url)
                        confirmed_hits.append(res)
                    else:
                        logger.info(f"      ❌ Skip: {res.item_name} ({res.reasoning})")

            # Save verified hits (or update scan status)
            self.presenter.save_results(confirmed_hits, task.name, total_scanned=len(ads_to_analyze))
        else:
            # Update status even if no candidates
            self.presenter.save_results([], task.name, total_scanned=0)

        logger.info(f"✨ Task '{task.name}' finished.")
        return seen_urls
