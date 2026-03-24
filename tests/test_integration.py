import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.orchestrator import ScraperOrchestrator
from src.models import ScrapeTask, SearchPageSource, CandidateItem, ProductCheck

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_run_task_flow(self):
        # 1. Setup Mocks
        analyzer = AsyncMock()
        content_fetcher = MagicMock()
        # Mocking fetch_ad_content as async since it is awaited in orchestrator
        content_fetcher.fetch_ad_content = AsyncMock()
        notification_service = MagicMock()
        presenter = MagicMock()
        crawler = MagicMock()
        
        # 2. Configure Mock behavior
        task = ScrapeTask(name="Test Task", search_query="XTZ", fuzzy_search=False)
        target_sites = ["site.com"]
        
        analyzer.get_search_urls.return_value = [
            SearchPageSource(site_name="site.com", search_url="https://site.com/search?q=XTZ")
        ]
        
        # Mock search page content
        content_fetcher.fetch_ad_content.side_effect = [
            "Search results page content with item 1", # First call for search page
            "Ad page content for item 1"               # Second call for deep dive
        ]
        
        # Mock candidate extraction
        analyzer.analyze_search_page.return_value = [
            CandidateItem(url="/item/1", title="XTZ Sub", price="1000", reasoning="Looks good", confidence_score=90)
        ]
        
        content_fetcher.fix_relative_url.return_value = "https://site.com/item/1"
        content_fetcher.is_valid_ad_link.return_value = True
        
        # Mock batch verification
        analyzer.analyze_batch.return_value = [
            ProductCheck(url="https://site.com/item/1", found_item=True, item_name="XTZ Sub", price="1000", reasoning="Perfect match")
        ]
        
        # 3. Initialize Orchestrator and run
        orchestrator = ScraperOrchestrator(
            analyzer=analyzer,
            content_fetcher=content_fetcher,
            notification_service=notification_service,
            presenter=presenter,
            target_sites=target_sites
        )
        
        seen_urls = []
        final_seen = await orchestrator.run_task(task, crawler, seen_urls)
        
        # 4. Verify results
        self.assertIn("https://site.com/item/1", final_seen)
        notification_service.notify_start.assert_called_once_with("Test Task")
        notification_service.notify_match.assert_called_once()
        presenter.save_results.assert_called_once()
        
        # Verify calls
        analyzer.get_search_urls.assert_called_once()
        analyzer.analyze_search_page.assert_called_once()
        analyzer.analyze_batch.assert_called_once()

if __name__ == "__main__":
    unittest.main()
