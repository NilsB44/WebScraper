import asyncio
import logging
import re
import urllib.parse
from typing import Any, Type

from google import genai
from pydantic import BaseModel

from src.models import BatchProductCheck, ProductCheck, SearchPageSource, SearchURLGenerator

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    # Maintainable search URL templates
    SEARCH_TEMPLATES: dict[str, str] = {
        "blocket.se": "https://www.blocket.se/annonser/hela_sverige?q={q}",
        "tradera.com": "https://www.tradera.com/search?q={q}",
        "kleinanzeigen.de": "https://www.kleinanzeigen.de/s-suchanfrage.html?keywords={q}",
        "hifitorget.se": "https://hifitorget.se/index.php?mod=search&searchstring={q}",
        "ebay.de": "https://www.ebay.de/sch/i.html?_nkw={q}",
        "dba.dk": "https://www.dba.dk/soeg/?soeg={q}",
        "finn.no": "https://www.finn.no/bap/forsale/search.html?q={q}"
    }

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        self.client = genai.Client(api_key=api_key)

    def _sanitize_input(self, text: str, max_length: int = 200) -> str:
        """
        Sanitize input using an allow-list of safe characters.
        Allow-list: alphanumeric, whitespace, and & + / . , ! ? ( ) @ # $ € £ k r and -
        """
        if not text:
            return ""
        # Remove characters not in the allow-list
        clean = re.sub(r"[^a-zA-Z0-9\s&+/.,!?()@#$€£kr-]", "", text)
        # Prevent prompt injection by neutralizing potential delimiters
        clean = clean.replace("---", " - ")
        return clean[:max_length].strip()

    async def generate_content_safe(self, prompt: str, schema: Type[BaseModel]) -> Any | None:
        """Tries multiple models to generate content, handling quotas with backoff."""
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
        ]

        for i, model in enumerate(models_to_try):
            try:
                delay = 2 + (i * 2) 
                await asyncio.sleep(delay)
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    },
                )
                return response
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ["429", "quota", "503", "overload"]):
                    logger.warning(f"   [QUOTA] {model} quota/overload. Trying next...")
                    continue
                elif "404" in err:
                    continue
                logger.error(f"   ❌ Error with {model}: {e}")

        return None

    async def get_search_urls(self, item_name: str, target_sites: list[str]) -> list[SearchPageSource]:
        sanitized_item = self._sanitize_input(item_name)
        sanitized_sites = [self._sanitize_input(site) for site in target_sites if site]
        
        prompt = f"""
        I want to buy a '{sanitized_item}'.
        Generate direct search result URLs for these marketplaces: {', '.join(sanitized_sites)}.

        CRITICAL URL RULES:
        - Blocket: 'https://www.blocket.se/annonser/hela_sverige?q=...'
        - Tradera: 'https://www.tradera.com/search?q=...'
        - Kleinanzeigen: 'https://www.kleinanzeigen.de/s-suchanfrage.html?keywords=...'
        - Hifitorget: 'https://hifitorget.se/index.php?mod=search&searchstring=...'
        - eBay DE: 'https://www.ebay.de/sch/i.html?_nkw=...'
        - DBA: 'https://www.dba.dk/soeg/?soeg=...'
        - Finn: 'https://www.finn.no/bap/forsale/search.html?q=...'

        Example Output:
        {{
          "search_pages": [
            {{"site_name": "blocket.se", "search_url": "https://www.blocket.se/annonser/hela_sverige?q=XTZ+12.17+Edge+Subwoofer"}},
            ...
          ]
        }}

        Return exactly the requested JSON format.
        """
        response = await self.generate_content_safe(prompt, SearchURLGenerator)
        
        results: list[SearchPageSource] = []
        if response and response.parsed:
            results = response.parsed.search_pages
            
        if not results:
            logger.warning("⚠️ Gemini failed to generate URLs. Using local heuristics failover.")
            # Secure URL encoding for query parameters
            q: str = urllib.parse.quote_plus(sanitized_item)
            for site in target_sites:
                if site in self.SEARCH_TEMPLATES:
                    url: str = self.SEARCH_TEMPLATES[site].format(q=q)
                    results.append(SearchPageSource(site_name=site, search_url=url))
                else:
                    logger.warning(f"   ⚠️ No local failover template for site: {site}")
                    
        return results

    async def analyze_batch(self, item_name: str, ads: list[dict[str, str]]) -> list[ProductCheck] | None:
        if not ads:
            return []

        sanitized_item = self._sanitize_input(item_name)
        prompt = (
            f"I am looking for: {sanitized_item}\n\n"
            f"Here are {len(ads)} advertisements to check:\n\n"
        )
        for i, ad in enumerate(ads):
            clean_url = self._sanitize_input(ad['url'], max_length=500)
            clean_content = self._sanitize_input(ad['content'], max_length=2000)
            prompt += f"--- AD #{i+1} ({ad['site']}) ---\nURL: {clean_url}\nCONTENT: {clean_content}\n\n"

        prompt += """
        --------------------------------------------------
        INSTRUCTIONS:
        Return a JSON object with a 'results' list.
        For EACH ad above, provide:
        1. 'url': The URL provided.
        2. 'found_item': boolean (TRUE only if it is the EXACT item I want).
        3. 'item_name': The clear name of the item for sale.
        4. 'price': The price with currency.
        5. 'reasoning': Brief explanation.
        """

        response = await self.generate_content_safe(prompt, BatchProductCheck)
        if response and response.parsed:
            return response.parsed.results
        
        logger.error("❌ Batch analysis failed: All AI models returned errors (quota/overload).")
        return None
