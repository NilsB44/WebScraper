import unittest
from unittest.mock import MagicMock, patch

from src.models import SearchPageSource, SearchURLGenerator
from src.services.analysis import GeminiAnalyzer


class TestAnalysis(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        # Patch the genai.Client to avoid real API calls
        with patch("google.genai.Client"):
            self.analyzer = GeminiAnalyzer(api_key="fake_key")

    async def test_get_search_urls_known_sites(self) -> None:
        target_sites = ["blocket.se", "tradera.com"]
        urls = await self.analyzer.get_search_urls("XTZ 12.17", target_sites)

        self.assertEqual(len(urls), 2)
        self.assertTrue(any("blocket.se" in u.search_url for u in urls))
        self.assertTrue(any("tradera.com" in u.search_url for u in urls))
        # Check that query is escaped
        self.assertTrue(any("XTZ+12.17" in u.search_url or "XTZ%2B12.17" in u.search_url for u in urls))

    async def test_get_search_urls_unknown_site(self) -> None:
        # Mock generate_content_safe to return a custom response for an unknown site
        mock_response = MagicMock()
        mock_response.parsed = SearchURLGenerator(
            search_pages=[SearchPageSource(site_name="unknown.site", search_url="https://unknown.site/search?q=XTZ")]
        )

        with patch.object(GeminiAnalyzer, "generate_content_safe", return_value=mock_response):
            target_sites = ["unknown.site"]
            urls = await self.analyzer.get_search_urls("XTZ", target_sites)

            self.assertEqual(len(urls), 1)
            self.assertEqual(urls[0].site_name, "unknown.site")
            self.assertEqual(urls[0].search_url, "https://unknown.site/search?q=XTZ")

    async def test_sanitize_input(self) -> None:

        dirty = "Hello World! <script>alert(1)</script> @#$€ äöå"
        clean = self.analyzer._sanitize_input(dirty)
        # Check that it preserves allowed characters and removes others if necessary
        # The current regex is [^a-zA-Z0-9\s&+/.,!?()@#$€£kr\-äöåÄÖÅéèáàüß]
        self.assertIn("Hello World!", clean)
        self.assertIn("äöå", clean)
        self.assertIn("@#$€", clean)
        self.assertNotIn("<script>", clean)
        self.assertNotIn("</script>", clean)

if __name__ == "__main__":
    unittest.main()
