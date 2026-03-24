import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.orchestrator import ScraperOrchestrator
from src.models import ScrapeTask, SearchPageSource, CandidateItem, ProductCheck

class TestScenarios(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.analyzer = AsyncMock()
        self.content_fetcher = MagicMock()
        self.content_fetcher.fetch_ad_content = AsyncMock()
        self.notification_service = MagicMock()
        self.presenter = MagicMock()
        self.crawler = MagicMock()
        self.target_sites = ["site.com"]
        
        self.orchestrator = ScraperOrchestrator(
            analyzer=self.analyzer,
            content_fetcher=self.content_fetcher,
            notification_service=self.notification_service,
            presenter=self.presenter,
            target_sites=self.target_sites
        )

    async def test_no_candidates_scenario(self):
        task = ScrapeTask(name="Empty Task", search_query="NonExistent")
        self.analyzer.get_search_urls.return_value = [
            SearchPageSource(site_name="site.com", search_url="https://site.com/search")
        ]
        self.content_fetcher.fetch_ad_content.return_value = "Empty page"
        self.analyzer.analyze_search_page.return_value = []
        
        final_seen = await self.orchestrator.run_task(task, self.crawler, [])
        
        self.assertEqual(len(final_seen), 0)
        self.presenter.save_results.assert_called_once_with([], "Empty Task", total_scanned=0)

    async def test_fuzzy_search_scenarios(self):
        task = ScrapeTask(name="Fuzzy Task", search_query="XTZ", fuzzy_search=True)
        self.analyzer.generate_query_variations.return_value = ["XTZ Sub", "XTZ 12.17"]
        
        # Mock get_search_urls to return one URL for each query (original + 2 variations)
        self.analyzer.get_search_urls.side_effect = [
            [SearchPageSource(site_name="site.com", search_url="url1")],
            [SearchPageSource(site_name="site.com", search_url="url2")],
            [SearchPageSource(site_name="site.com", search_url="url3")]
        ]
        
        self.content_fetcher.fetch_ad_content.return_value = "content"
        self.analyzer.analyze_search_page.return_value = []
        
        await self.orchestrator.run_task(task, self.crawler, [])
        
        # Verify 3 search URL calls (1 original + 2 variations)
        self.assertEqual(self.analyzer.get_search_urls.call_count, 3)

    async def test_skip_seen_urls(self):
        task = ScrapeTask(name="Seen Task", search_query="XTZ")
        self.analyzer.get_search_urls.return_value = [
            SearchPageSource(site_name="site.com", search_url="search_url")
        ]
        self.content_fetcher.fetch_ad_content.return_value = "content"
        self.analyzer.analyze_search_page.return_value = [
            CandidateItem(url="seen_url", title="Seen", price="100", reasoning="r", confidence_score=100),
            CandidateItem(url="new_url", title="New", price="200", reasoning="r", confidence_score=100)
        ]
        self.content_fetcher.fix_relative_url.side_effect = lambda b, h: h
        self.content_fetcher.is_valid_ad_link.return_value = True
        
        # seen_url is already in the list
        seen_urls = ["seen_url"]
        
        # It should only deep dive into "new_url"
        final_seen = await self.orchestrator.run_task(task, self.crawler, seen_urls)
        
        # Should contain both now
        self.assertIn("seen_url", final_seen)
        self.assertIn("new_url", final_seen)
        
        # fetch_ad_content should be called: 1 (search page) + 1 (new_url deep dive) = 2
        # (It's NOT called for "seen_url")
        self.assertEqual(self.content_fetcher.fetch_ad_content.call_count, 2)

if __name__ == "__main__":
    unittest.main()
