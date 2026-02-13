import asyncio
import logging
import re
import urllib.parse
from typing import Any

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
        "finn.no": "https://www.finn.no/bap/forsale/search.html?q={q}",
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

    async def generate_content_safe(self, prompt: str, schema: type[BaseModel]) -> Any | None:
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
        """
        Generates search URLs. Prioritizes local templates to save Gemini tokens.
        Only asks Gemini for sites without a local template.
        """
        results: list[SearchPageSource] = []
        q: str = urllib.parse.quote_plus(item_name)

        remaining_sites = []
        for site in target_sites:
            if site in self.SEARCH_TEMPLATES:
                url = self.SEARCH_TEMPLATES[site].format(q=q)
                results.append(SearchPageSource(site_name=site, search_url=url))
            else:
                remaining_sites.append(site)

        if not remaining_sites:
            logger.info("✅ All search URLs generated from local templates (0 tokens used).")
            return results

        logger.info(f"🧠 Asking Gemini for search URLs for {len(remaining_sites)} unknown sites...")
        sanitized_item = self._sanitize_input(item_name)
        prompt = f"""
        I want to buy a '{sanitized_item}'.
        Generate direct search result URLs for these marketplaces: {", ".join(remaining_sites)}.
        Return exactly this JSON format:
        {{
          "search_pages": [
            {{"site_name": "site.com", "search_url": "https://site.com/search?q=..."}}
          ]
        }}
        """
        response = await self.generate_content_safe(prompt, SearchURLGenerator)
        if response and response.parsed:
            results.extend(response.parsed.search_pages)

        return results

    async def analyze_batch(self, item_name: str, ads: list[dict[str, str]]) -> list[ProductCheck] | None:
        if not ads:
            return []

        sanitized_item = self._sanitize_input(item_name)
        prompt = f"I am looking for: {sanitized_item}\n\nHere are {len(ads)} advertisements to check:\n\n"
        for i, ad in enumerate(ads):
            clean_url = self._sanitize_input(ad["url"], max_length=500)
            clean_content = self._sanitize_input(ad["content"], max_length=2000)
            prompt += f"--- AD #{i + 1} ({ad['site']}) ---\nURL: {clean_url}\nCONTENT: {clean_content}\n\n"

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
