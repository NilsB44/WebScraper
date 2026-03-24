import asyncio
import logging
import sys

from crawl4ai import AsyncWebCrawler  # type: ignore

from src.config import settings
from src.services.analysis import GeminiAnalyzer
from src.services.crawler import ContentFetcher
from src.services.notification import NotificationService
from src.services.orchestrator import ScraperOrchestrator
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

        orchestrator = ScraperOrchestrator(
            analyzer=analyzer,
            content_fetcher=content_fetcher,
            notification_service=notification_service,
            presenter=presenter,
            target_sites=settings.target_sites
        )
    except Exception as e:
        logger.critical(f"❌ Failed to initialize services: {e}")
        sys.exit(1)

    # Load history
    seen_urls = storage_service.load()
    logger.info(f"📜 Loaded {len(seen_urls)} previously seen items.")

    async with AsyncWebCrawler(config=content_fetcher.browser_config) as crawler:
        for task in settings.tasks:
            seen_urls = await orchestrator.run_task(task, crawler, seen_urls)

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
