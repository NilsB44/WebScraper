import asyncio
import logging
import sys

from crawl4ai import AsyncWebCrawler  # type: ignore

from src.config import settings
from src.models import (
    SearchPageSource,
)
from src.services.analysis import GeminiAnalyzer
from src.services.crawler import ContentFetcher
from src.services.notification import NotificationService
from src.services.presenter import ResultsPresenter
from src.services.storage import GitManager, HistoryManager

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("🚀 Starting AI-Driven Agentic Web Scraper...")

    # 1. Initialize Services
    try:
        notification_service = NotificationService(settings.ntfy_topic)
        storage_service = HistoryManager(settings.history_file)
        git_service = GitManager(settings.history_file, settings.git_user_name, settings.git_user_email)
        analyzer = GeminiAnalyzer(settings.gemini_api_key)
        content_fetcher = ContentFetcher(headless=settings.headless)
        presenter = ResultsPresenter()
    except Exception as e:
        logger.critical(f"❌ Failed to initialize services: {e}")
        sys.exit(1)

    # Load history
    seen_urls = storage_service.load()
    logger.info(f"📜 Loaded {len(seen_urls)} previously seen items.")

    async with AsyncWebCrawler(config=content_fetcher.browser_config) as crawler:
        for task in settings.tasks:
            logger.info(f"\n⚡ Starting Task: {task.name}")
            notification_service.notify_start(task.name)

            # A. Generate Queries / Direct URLs
            if task.search_query.startswith("http"):
                logger.info(f"   🔗 Direct URL detected: {task.search_query}")
                all_search_urls = [SearchPageSource(site_name="Direct", search_url=task.search_query)]
            else:
                queries = [task.search_query]
                if task.fuzzy_search:
                    variations = await analyzer.generate_query_variations(task.search_query)
                    queries.extend([v for v in variations if v not in queries])

                logger.info(f"   🔎 Searching for queries: {', '.join(queries)}")

                all_search_urls = []
                for q in queries:
                    urls = await analyzer.get_search_urls(q, settings.target_sites)
                    all_search_urls.extend(urls)

            ads_to_analyze: list[dict[str, str]] = []

            # B. Agentic Search Page Analysis
            for source in all_search_urls:
                logger.info(f"   🌐 Checking: {source.search_url}")

                list_content = await content_fetcher.fetch_ad_content(crawler, source.search_url)
                if not list_content:
                    continue

                candidates = await analyzer.analyze_search_page(list_content, task)

                if not candidates:
                    logger.info("   ℹ️ No candidates found on this page.")
                    continue

                logger.info(f"   ✅ Agent selected {len(candidates)} candidates.")

                # C. Deep Dive
                for cand in candidates:
                    if cand.url in seen_urls:
                        continue

                    full_url = content_fetcher.fix_relative_url(source.search_url, cand.url)
                    if not content_fetcher.is_valid_ad_link(full_url) or full_url in seen_urls:
                        continue

                    logger.info(f"      🕵️ Deep diving: {cand.title} ({cand.price})")

                    ad_content = await content_fetcher.fetch_ad_content(crawler, full_url)
                    if ad_content:
                        ads_to_analyze.append({"site": source.site_name, "url": full_url, "content": ad_content})
                        seen_urls.append(full_url)

            # D. Batch Verify
            if ads_to_analyze:
                item_label = task.name if task.search_query.startswith("http") else task.search_query
                logger.info(f"   🧠 Verifying {len(ads_to_analyze)} candidates for {item_label}...")
                results = await analyzer.analyze_batch(item_label, ads_to_analyze)

                confirmed_hits = []
                if results:
                    for res in results:
                        if res.found_item:
                            logger.info(f"      🎉 MATCH! {res.item_name} - {res.price}")
                            notification_service.notify_match(res.item_name, res.price, res.url)
                            confirmed_hits.append(res)
                        else:
                            logger.info(f"      ❌ Skip: {res.item_name} ({res.reasoning})")

                # Save verified hits (or update scan status)
                presenter.save_results(confirmed_hits, task.name, total_scanned=len(ads_to_analyze))
            else:
                # Update status even if no candidates
                presenter.save_results([], task.name, total_scanned=0)

            logger.info(f"✨ Task '{task.name}' finished.")

    storage_service.save(seen_urls)

    if settings.ci_mode:
        git_service.commit_and_push("chore: update seen items and results", branch="scraper-results")

    logger.info("💤 Scraper finished successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Scraper stopped by user.")
    except Exception as e:
        logger.critical(f"🔥 Critical failure: {e}")
        sys.exit(1)
