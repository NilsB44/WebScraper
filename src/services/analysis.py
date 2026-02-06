import logging
import time
from typing import List, Dict, Any, Optional
from google import genai
from src.models import SearchURLGenerator, SearchPageSource, BatchProductCheck, ProductCheck

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        self.client = genai.Client(api_key=api_key)

    def generate_content_safe(self, prompt: str, schema: Any) -> Optional[Any]:
        """Tries multiple models to generate content, handling quotas."""
        models_to_try = [
            "gemini-2.0-flash", 
            "gemini-1.5-flash-002",
            "gemini-2.5-flash-lite", 
            "gemini-3-flash-preview"
        ]
        
        for model in models_to_try:
            try:
                time.sleep(2) # Basic throttling
                response = self.client.models.generate_content(
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
                    # Model not found, skip quietly
                    continue
                logger.error(f"   ❌ Error with {model}: {e}")
        
        return None

    def get_search_urls(self, item_name: str, target_sites: List[str]) -> List[SearchPageSource]:
        prompt = f"""
        I want to buy a "{item_name}".
        Generate direct search result URLs for: {', '.join(target_sites)}.
        
        CRITICAL URL RULES:
        - Blocket: 'https://www.blocket.se/annonser/hela_sverige?q=...'
        - Tradera: 'https://www.tradera.com/search?q=...'
        - Kleinanzeigen: 'https://www.kleinanzeigen.de/s-suchanfrage.html?keywords=...'
        - Hifitorget: 'https://hifitorget.se/index.php?mod=search&searchstring=...'
        - eBay DE: 'https://www.ebay.de/sch/i.html?_nkw=...'
        - DBA: 'https://www.dba.dk/soeg/?soeg=...'
        - Finn: 'https://www.finn.no/bap/forsale/search.html?q=...'
        
        Return a list of objects with 'site_name' and 'search_url'.
        """
        response = self.generate_content_safe(prompt, SearchURLGenerator)
        if response and response.parsed:
            return response.parsed.search_pages
        return []

    def analyze_batch(self, item_name: str, ads: List[Dict[str, str]]) -> List[ProductCheck]:
        if not ads:
            return []
            
        prompt = f"I am looking for: {item_name}\n\nHere are {len(ads)} advertisements to check:\n\n"
        for i, ad in enumerate(ads):
            # Strict truncation to avoid token limits
            clean_content = ad['content'][:2000].replace("\n", " ") 
            prompt += f"--- AD #{i+1} ({ad['site']}) ---\nURL: {ad['url']}\nCONTENT: {clean_content}\n\n"
        
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
        
        response = self.generate_content_safe(prompt, BatchProductCheck)
        if response and response.parsed:
            return response.parsed.results
        return []