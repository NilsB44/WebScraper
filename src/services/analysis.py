import asyncio
import logging
import re
import urllib.parse
from typing import Any, cast

from google import genai
from pydantic import BaseModel

from src.models import (
    BatchProductCheck,
    CandidateItem,
    ProductCheck,
    QueryVariations,
    ScrapeTask,
    SearchPageAnalysis,
    SearchPageSource,
    SearchURLGenerator,
)
from src.utils.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    # Maintainable search URL templates
    SEARCH_TEMPLATES: dict[str, str] = {
        "blocket.se": "https://www.blocket.se/recommerce/forsale/search?q={q}",
        "tradera.com": "https://www.tradera.com/search?q={q}",
        "kleinanzeigen.de": "https://www.kleinanzeigen.de/s-suchanfrage.html?keywords={q}",
        "hifitorget.se": "https://hifitorget.se/index.php?mod=search&searchstring={q}",
        "ebay.de": "https://www.ebay.de/sch/i.html?_nkw={q}",
        "dba.dk": "https://www.dba.dk/soeg/?soeg={q}",
        "finn.no": "https://www.finn.no/bap/forsale/search.html?q={q}",
        "hifishark.com": "https://www.hifishark.com/search?q={q}",
    }

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        self.client = genai.Client(api_key=api_key)

    def _sanitize_input(self, text: str, max_length: int = 500) -> str:
        if not text:
            return ""
        # Allow more characters, especially for non-latin or special symbols in ads
        clean = re.sub(r"[^a-zA-Z0-9\s&+/.,!?()@#$€£kr\-äöåÄÖÅéèáàüß]", "", text)
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
                # Jittered backoff to avoid synchronized spikes
                delay = (i * 5) + 2
                await asyncio.sleep(delay)

                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    },
                )
                UsageTracker.log_use(model=model)
                return response
            except Exception as e:
                UsageTracker.log_use(model=model, calls=1)  # Log the attempt even if it fails
                err = str(e).lower()

                if any(x in err for x in ["429", "quota", "503", "overload"]):
                    logger.warning(f"   [QUOTA] {model} overloaded. Retrying with next model...")
                    continue
                elif "404" in err:
                    continue
                logger.error(f"   ❌ Error with {model}: {e}")

        return None

    async def generate_query_variations(self, query: str) -> list[str]:
        """Generates fuzzy variations of a search query."""
        logger.info(f"   🧠 Generating fuzzy variations for: {query}...")
        prompt = f"""
        Generate 3-4 short, effective search query variations for finding this item second-hand: "{query}".
        Focus on common misspellings, partial names, or alternative terms.
        Return a JSON object with a 'variations' list of strings.
        """
        response = await self.generate_content_safe(prompt, QueryVariations)
        if response and response.parsed:
            return cast(list[str], response.parsed.variations)
        return [query]

    async def get_search_urls(self, item_name: str, target_sites: list[str]) -> list[SearchPageSource]:
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
            results.extend(cast(list[SearchPageSource], response.parsed.search_pages))

        return results

    async def analyze_search_page(self, content: str, task: ScrapeTask) -> list[CandidateItem]:
        logger.info(f"   🧠 Agentic Analysis of search page for '{task.name}'...")

        price_instruction = ""
        if task.max_price:
            price_instruction = (
                f"IMPORTANT: Filter out any items strictly MORE expensive than {task.max_price} {task.currency}."
            )

        prompt = f"""
        I am looking for: {task.search_query}
        Description/Context: {task.description}
        {price_instruction}

        Below is the text content from a search results page.
        Your goal is to extract ALL potential matches for the search query.

        PAGE CONTENT:
        --------------------------------------------------
        {content[:150000]}
        --------------------------------------------------

        INSTRUCTIONS:
        1. List candidates that are for sale (Ignore 'Wanted', 'Looking for', 'Sold', or 'Bought').
        2. Extract the URL (may be relative), the Title, and the Price.
        3. Search for patterns like 'kr', 'EUR', '€', '£', or 'Price:' to find item entries.
        4. Assign a confidence score (0-100) based on how well it matches "{task.search_query}".
        5. If the page explicitly says 'No results' or similar, return an empty list.
        6. Focus on the main result list, skip sidebar 'sponsored' ads if they are irrelevant.
        7. If you see multiple items, list them all.
        8. {price_instruction}

        Return exactly a JSON object with a 'candidates' list.
        """

        response = await self.generate_content_safe(prompt, SearchPageAnalysis)
        if response and response.parsed:
            candidates = cast(list[CandidateItem], response.parsed.candidates)
            # Relaxed confidence score to 50 for broader initial selection
            return [c for c in candidates if c.confidence_score >= 50]

        return []

    async def analyze_batch(self, item_name: str, ads: list[dict[str, str]]) -> list[ProductCheck] | None:
        if not ads:
            return []

        sanitized_item = self._sanitize_input(item_name)
        prompt = f"I am looking for: {sanitized_item}\n\nHere are {len(ads)} advertisements to check:\n\n"
        for i, ad in enumerate(ads):
            clean_url = self._sanitize_input(ad["url"], max_length=500)
            clean_content = self._sanitize_input(ad["content"], max_length=5000)
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
            return cast(list[ProductCheck] | None, response.parsed.results)

        return None
