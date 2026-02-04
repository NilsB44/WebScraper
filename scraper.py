import asyncio
import os
import requests
from googlesearch import search
from crawl4ai import AsyncWebCrawler
from google import genai
from pydantic import BaseModel

# --- CONFIGURATION ---
SEARCH_QUERY = "Second hand active subwoofer sale europe site:blocket.se OR site:kleinanzeigen.de"
NTFY_TOPIC = "my_subwoofer_alerts_123" # CHANGE THIS to something unique
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# --- DATA MODELS ---
class ProductCheck(BaseModel):
    found_item: bool
    item_name: str
    price: str
    url: str
    reasoning: str

client = genai.Client(api_key=GEMINI_API_KEY)

async def main():
    print(f"🕵️ Agent starting search for: {SEARCH_QUERY}")
    
    # 1. DISCOVERY PHASE: Find relevant URLs via Google
    # We ask for 5 results to keep it fast/free
    found_urls = list(search(SEARCH_QUERY, num_results=5, advanced=True))
    urls_to_scrape = [result.url for result in found_urls]
    
    print(f"🔗 Found {len(urls_to_scrape)} potential links: {urls_to_scrape}")

    # 2. SCRAPING PHASE: Visit each URL
    async with AsyncWebCrawler(verbose=True) as crawler:
        for url in urls_to_scrape:
            try:
                print(f"Processing: {url}...")
                result = await crawler.arun(url=url)
                
                # 3. ANALYSIS PHASE: Ask Gemini
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"""
                    You are a shopping assistant. Analyze this webpage content:
                    {result.markdown[:10000]} # Limit text to avoid token limits
                    
                    Task: Look for a high-quality active subwoofer for sale.
                    Ignore 'wanted' ads or spare parts. 
                    If multiple items are listed, pick the best deal.
                    """,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ProductCheck,
                    },
                )
                
                analysis = response.parsed
                
                # 4. NOTIFICATION PHASE
                if analysis.found_item:
                    print(f"✅ Match found: {analysis.item_name}")
                    message = f"Found: {analysis.item_name}\nPrice: {analysis.price}\nReason: {analysis.reasoning}\nLink: {analysis.url}"
                    requests.post(
                        f"https://ntfy.sh/{NTFY_TOPIC}", 
                        data=message.encode("utf-8"),
                        headers={"Title": "Subwoofer Alert! 🔊"}
                    )
                else:
                    print("❌ No matching items on this page.")

            except Exception as e:
                print(f"⚠️ Error processing {url}: {e}")

if __name__ == "__main__":
    asyncio.run(main())