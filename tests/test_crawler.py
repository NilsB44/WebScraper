import unittest
from src.services.crawler import ContentFetcher

class TestCrawler(unittest.TestCase):
    def test_is_valid_ad_link(self):
        valid_urls = [
            "https://www.blocket.se/annons/stockholm/xtz_12_17_edge/12345678",
            "https://www.tradera.com/item/12345678",
            "https://www.kleinanzeigen.de/s-anzeige/xtz-12-17-subwoofer/123456789-172-3378",
            "https://hifitorget.se/visa_annons.php?id=123456",
            "https://www.ebay.de/itm/123456789012",
            "https://www.finn.no/bap/forsale/ad.html?finnkode=123456789",
            "https://www.hifishark.com/model/xtz-99-w12-16",
        ]
        invalid_urls = [
            "https://www.google.com",
            "https://www.blocket.se",
            "https://www.tradera.com/search?q=xtz",
            "https://www.dba.dk/soeg/?soeg=xtz",
        ]
        
        for url in valid_urls:
            self.assertTrue(ContentFetcher.is_valid_ad_link(url), f"Failed for {url}")
            
        for url in invalid_urls:
            self.assertFalse(ContentFetcher.is_valid_ad_link(url), f"Failed for {url}")

if __name__ == "__main__":
    unittest.main()
