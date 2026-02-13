import asyncio
import logging
import sys

from crawl4ai import AsyncWebCrawler

from src.config import settings
from src.services.analysis import GeminiAnalyzer
from src.services.crawler import ContentFetcher
from src.services.notification import NotificationService
from src.services.storage import GitManager, HistoryManager

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ScraperBot")

async def main():
    logger.info(f"🕵️ Agent starting SNIPER RUN for: {settings.item_name}")

    # Initialize Services
    history_manager = HistoryManager(settings.history_file)
    git_manager = GitManager(settings.history_file, settings.git_user_name, settings.git_user_email)
    notification_service = NotificationService(settings.ntfy_topic)
    analyzer = GeminiAnalyzer(settings.gemini_api_key)
    fetcher = ContentFetcher(headless=settings.headless)

    seen_urls = history_manager.load()

    # 1. Plan
    logger.info("🧠 Asking Gemini to generate search URLs...")
    search_pages = await analyzer.get_search_urls(settings.item_name, settings.target_sites)
    logger.info(f"📍 Agent generated {len(search_pages)} paths.")

    # 2. Test Notification (only on fresh start)
    if not seen_urls:
        logger.info("🔔 Sending start notification...")
        notification_service.notify_start(settings.item_name)

    found_something_new = False

    # 3. Execute
    async with AsyncWebCrawler(config=fetcher.browser_config) as crawler:
        ads_to_analyze = []

        for page in search_pages:
            logger.info(f"🚜 Harvesting {page.site_name}: {page.search_url}")
            await asyncio.sleep(2) # Politeness delay

            try:
                # Use arun directly as it was most reliable
                result = await crawler.arun(url=page.search_url, config=fetcher.run_config)

                if not result.success:
                    logger.warning("⚠️ Failed to load list page")
                    continue

                all_links = []
                if result.links and "internal" in result.links:
                    all_links = [l.get("href", "") for l in result.links["internal"]]

                total_found = len(all_links)
                ad_candidates = []

                for href in all_links:
                    full_url = fetcher.fix_relative_url(page.search_url, href)
                    if fetcher.is_valid_ad_link(full_url):
                        ad_candidates.append(full_url)

                ad_candidates = list(set(ad_candidates)) # Deduplicate URLs
                irrelevant_count = total_found - len(ad_candidates)

                new_candidates = [c for c in ad_candidates if c not in seen_urls]
                seen_count = len(ad_candidates) - len(new_candidates)

                logger.info(f"   📊 Results: {total_found} links found | {irrelevant_count} irrelevant | {seen_count} already seen | {len(new_candidates)} NEW ads")

                if not new_candidates:
                    continue

                num_to_check = min(len(new_candidates), 5)
                logger.info(f"   -> Queuing TOP {num_to_check} for analysis...")

                for ad_url in new_candidates[:num_to_check]:
                    content = await fetcher.fetch_ad_content(crawler, ad_url)

                    if not content:
                        logger.warning("   ⚠️ Content empty. Skipping.")
                        continue

                    ads_to_analyze.append({
                        "url": ad_url,
                        "content": content,
                        "site": page.site_name
                    })
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"⚠️ Harvesting error: {e}")

        # 4. Batch Analyze
        if ads_to_analyze:
            logger.info(f"🧠 Sending BATCH analysis for {len(ads_to_analyze)} items...")
            results = await analyzer.analyze_batch(settings.item_name, ads_to_analyze)

            for res in results:
                # Add to seen URLs regardless of match to avoid re-checking
                if res.url not in seen_urls:
                    seen_urls.append(res.url)

                if res.found_item:
                    logger.info(f"   ✅ MATCH! {res.item_name}")
                    notification_service.notify_match(res.item_name, res.price, res.url)
                    found_something_new = True
                else:
                    logger.info(f"   ❌ {res.item_name} ({res.reasoning})")

    # 5. Save
    history_manager.save(seen_urls)

    if found_something_new:
        if settings.ci_mode:
            git_manager.commit_and_push(f"🤖 Update history for {settings.item_name}")
        else:
            logger.info("💾 Local run: Skipping Git commit.")
    else:
        logger.info("💤 Scan complete. No new matches found.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Scraper stopped by user.")
    except Exception as e:
        logger.critical(f"🔥 Critical failure: {e}")
        sys.exit(1)
