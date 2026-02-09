import asyncio
import logging
import re
from typing import Any, Type

from google import genai
from pydantic import BaseModel

from src.models import BatchProductCheck, ProductCheck, SearchPageSource, SearchURLGenerator

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        self.client = genai.Client(api_key=api_key)

    def _sanitize_input(self, text: str, max_length: int = 200) -> str:
        """
        Sanitize input using an allow-list of safe characters.
        Allows alphanumeric, common punctuation, and product-relevant symbols (&, +, /, currency).
        """
        if not text:
            return ""
        # Broadened allow-list: alphanumeric, whitespace, and & + / . , - ! ? ( ) @ # $ € £ kr
        clean = re.sub(r"[^a-zA-Z0-9\s\&\+\/\.\,\-\!\?\(\)\@\#\$\€\£\kr]", "", text)
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
                # Dynamic delay: start with 2s, increase if we are deep in fallbacks
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
        if response and response.parsed:
            return response.parsed.search_pages
        return []

    async def analyze_batch(self, item_name: str, ads: list[dict[str, str]]) -> list[ProductCheck]:
        if not ads:
            return []

        sanitized_item = self._sanitize_input(item_name)
        prompt = f"I am looking for: {sanitized_item}

Here are {len(ads)} advertisements to check:

"
        for i, ad in enumerate(ads):
            # Sanitize all external fields
            clean_url = self._sanitize_input(ad["url"], max_length=500)
            clean_content = self._sanitize_input(ad["content"], max_length=2000)
            prompt += f"--- AD #{i+1} ({ad['site']}) ---
URL: {clean_url}
CONTENT: {clean_content}

"

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
        return []
