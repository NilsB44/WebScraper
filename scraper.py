import asyncio
import logging
import sys

from crawl4ai import AsyncWebCrawler  # type: ignore

from src.config import settings
from src.services.analysis import GeminiAnalyzer
from src.services.crawler import ContentFetcher
from src.services.notification import NotificationService
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
    except Exception as e:
        logger.critical(f"❌ Failed to initialize services: {e}")
        sys.exit(1)

    # Load history
    seen_urls = storage_service.load()
    logger.info(f"📜 Loaded {len(seen_urls)} previously seen items.")

    found_something_new = False

    # Start the browser session ONCE for efficiency
    async with AsyncWebCrawler(config=content_fetcher.browser_config) as crawler:

        # 2. Iterate through Tasks (Multi-Path)
        for task in settings.tasks:
            logger.info(f"\n⚡ Starting Task: {task.name}")
            logger.info(f"   🔎 Query: {task.search_query}")

            notification_service.notify_start(task.name)

            # A. Get Search URLs
            try:
                search_urls = await analyzer.get_search_urls(task.search_query, settings.target_sites)
            except Exception as e:
                logger.error(f"   ❌ Failed to generate search URLs for {task.name}: {e}")
                continue

            ads_to_analyze: list[dict[str, str]] = []

            # B. Agentic Search Page Analysis
            for source in search_urls:
                logger.info(f"   🌐 Checking list page: {source.search_url}")

                # Fetch content of the SEARCH RESULTS page
                list_content = await content_fetcher.fetch_ad_content(crawler, source.search_url)
                if not list_content:
                    logger.warning(f"   ⚠️ Failed to fetch list page: {source.search_url}")
                    continue

                # Ask Gemini to pick candidates from this list
                candidates = await analyzer.analyze_search_page(list_content, task)

                if not candidates:
                    logger.info("   👀 No interesting candidates found on this page.")
                    continue

                logger.info(f"   ✅ Agent selected {len(candidates)} candidates for deep dive.")

                # C. Fetch Details for Selected Candidates
                for cand in candidates:
                    if cand.url in seen_urls:
                        continue

                    # Double check url validity
                    if not content_fetcher.is_valid_ad_link(cand.url):
                        # Sometimes LLM extracts partial URLs or junk
                        full_url = content_fetcher.fix_relative_url(source.search_url, cand.url)
                        if not content_fetcher.is_valid_ad_link(full_url):
                            continue
                        cand.url = full_url

                    if cand.url in seen_urls:
                        continue

                    logger.info(f"      🕵️ Deep diving: {cand.title} ({cand.price})")

                    # Fetch Ad Content
                    ad_content = await content_fetcher.fetch_ad_content(crawler, cand.url)
                    if ad_content:
                        ads_to_analyze.append({
                            "site": source.site_name,
                            "url": cand.url,
                            "content": ad_content
                        })
                        seen_urls.append(cand.url) # Mark as seen so we don't re-check next run

            # D. Batch Verify (Final Guardrail)
            if ads_to_analyze:
                logger.info(f"   🧠 Verifying {len(ads_to_analyze)} candidates for {task.name}...")
                results = await analyzer.analyze_batch(task.search_query, ads_to_analyze)

                if results:
                    for res in results:
                        if res.found_item:
                            logger.info(f"      🎉 CONFIRMED MATCH! {res.item_name} - {res.price}")
                            notification_service.notify_match(res.item_name, res.price, res.url)
                            found_something_new = True
                        else:
                            logger.info(f"      ❌ False positive: {res.item_name} ({res.reasoning})")

            logger.info(f"✨ Task '{task.name}' finished.")

    # 3. Save & Commit
    storage_service.save(seen_urls)

    if found_something_new and settings.ci_mode:
        git_service.commit_and_push("update: seen items (found new matches)")
    elif settings.ci_mode:
        git_service.commit_and_push("update: seen items (sync)")

    logger.info("💤 Scraper finished successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Scraper stopped by user.")
    except Exception as e:
        logger.critical(f"🔥 Critical failure: {e}")
        sys.exit(1)
