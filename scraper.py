import asyncio
import os
import json
import requests
import subprocess
import time
from crawl4ai import AsyncWebCrawler
from google import genai
from pydantic import BaseModel
from typing import List

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# --- ⚙️ USER CONFIGURATION -----------------------
ITEM_NAME = "XTZ 12.17 Edge Subwoofer"

TARGET_SITES = [
    "blocket.se", 
    "tradera.com", 
    "hifitorget.se", 
    "kleinanzeigen.de", 
    "ebay.de", 
    "dba.dk",     # Denmark
    "finn.no"     # Norway
]
NTFY_TOPIC = "gemini_and_nils_subscribtion_service"
HISTORY_FILE = "seen_items.json"
# -------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class SearchPageSource(BaseModel):
    site_name: str
    search_url: str

class SearchURLGenerator(BaseModel):
    search_pages: List[SearchPageSource]

class ProductCheck(BaseModel):
    url: str
    found_item: bool
    item_name: str
    price: str
    reasoning: str

class BatchProductCheck(BaseModel):
    results: List[ProductCheck]

client = genai.Client(api_key=GEMINI_API_KEY)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def git_commit_changes():
    try:
        if not os.environ.get("CI"):
            print("💾 Local run: Skipping Git commit.")
            return
        subprocess.run(["git", "config", "--global", "user.name", "Scraper Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@github.com"], check=True)
        subprocess.run(["git", "add", HISTORY_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "🤖 Update seen items history"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("💾 History updated and pushed to repo.")
    except Exception as e:
        print(f"⚠️ Could not push history: {e}")

async def main():
    print(f"🕵️ Agent starting SNIPER RUN for: {ITEM_NAME}")
    seen_urls = load_history()
    
    # --- STEP 1: PLAN ---
    print(f"🧠 Asking Gemini to generate search URLs...")
    
    prompt_generate = f"""
    I want to buy a "{ITEM_NAME}".
    Generate direct search result URLs for: {', '.join(TARGET_SITES)}.
    
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
    
    def call_gemini(contents, schema):
        # Using models that usually have better free tier availability
        models_to_try = [
            "gemini-2.0-flash", 
            "gemini-1.5-flash-002",
            "gemini-2.5-flash-lite", 
            "gemini-3-flash-preview"
        ]
        
        for model_name in models_to_try:
            try:
                # Add a small delay BEFORE the call to respect the 5 RPM limit
                time.sleep(12) 
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    },
                )
                return response
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str:
                    print(f"   ⚠️ {model_name} quota hit. Trying next...")
                    continue
                elif "404" in err_str:
                    # Some models might not be enabled for your key yet
                    continue
                print(f"   ❌ Error with {model_name}: {e}")
                continue
        return None

    response_plan = call_gemini(prompt_generate, SearchURLGenerator)
    if not response_plan:
        print("❌ All models failed (likely quota).")
        return
    
    search_pages = response_plan.parsed.search_pages
    print(f"📍 Agent generated {len(search_pages)} paths.")

    # --- TEST NOTIFICATION ---
    if not seen_urls: # Only test on first run or if history cleared
        print(f"🔔 Sending test notification to {NTFY_TOPIC}...")
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"Scraper started for {ITEM_NAME}!".encode("utf-8"), headers={"Title": "Scraper Online", "Priority": "1"})

    found_something_new = False
    
    # --- STEP 2: EXECUTE ---
    # Using a robust browser config to bypass blocks
    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-blink-features=AutomationControlled"], # Helps avoid detection
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        
        ads_to_analyze = []

        for page in search_pages:
            list_url = page.search_url
            print(f"\n🚜 Harvesting {page.site_name}: {list_url}")
            time.sleep(2) 

            try:
                result = await crawler.arun(
                    url=list_url,
                    wait_until="networkidle",
                    delay_before_return_html=5.0,
                    bypass_cache=True
                )
                if not result.success:
                    print(f"⚠️ Failed to load list page")
                    continue

                candidates = []
                for link in result.links.get("internal", []):
                    href = link.get("href", "")
                    
                    # Fix relative links
                    if not href.startswith("http"):
                        if "tradera.com" in list_url: href = "https://www.tradera.com" + href
                        elif "blocket.se" in list_url: href = "https://www.blocket.se" + href
                        elif "kleinanzeigen.de" in list_url: href = "https://www.kleinanzeigen.de" + href
                        elif "hifitorget.se" in list_url: href = "https://hifitorget.se/" + href
                        elif "ebay.de" in list_url: href = "https://www.ebay.de" + href
                        elif "dba.dk" in list_url: href = "https://www.dba.dk" + href
                        elif "finn.no" in list_url: href = "https://www.finn.no" + href

                    if ("/annons/" in href or "/item/" in href or "/s-anzeige/" in href or "/advert/" in href or "/itm/" in href or "id=" in href) and len(href) > 20:
                        candidates.append(href)

                new_candidates = [c for c in set(candidates) if c not in seen_urls]
                
                if not new_candidates:
                    print("   -> No new ads found here.")
                    continue

                # Check more ads now that we have better logic
                num_to_check = min(len(new_candidates), 5)
                print(f"   -> Found {len(new_candidates)} new ads. Queuing TOP {num_to_check} for analysis...")
                
                for ad_url in new_candidates[:num_to_check]:
                    print(f"   📥 Fetching content: {ad_url}")
                    
                    # Attempt 1: Standard Crawler
                    ad_result = await crawler.arun(
                        url=ad_url, 
                        wait_until="networkidle",
                        delay_before_return_html=8.0,
                        bypass_cache=True
                    )
                    
                    content = ad_result.markdown or ad_result.html[:30000]
                    
                    # Attempt 2: Fallback to requests with browser headers for Schibsted sites
                    if (not content or len(content) < 200) and ("blocket.se" in ad_url or "finn.no" in ad_url):
                        print(f"   ⚠️ Crawler blocked. Trying requests fallback...")
                        try:
                            headers = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                                "Accept-Language": "en-US,en;q=0.5",
                            }
                            resp = requests.get(ad_url, headers=headers, timeout=10)
                            if resp.status_code == 200:
                                content = resp.text[:30000]
                                print(f"   ✅ Requests fallback worked ({len(content)} chars).")
                        except Exception as re:
                            print(f"   ❌ Fallback failed: {re}")
                    
                    if not content or len(content) < 200:
                        print(f"   ⚠️ Content still too short ({len(content) if content else 0} chars). Skipping.")
                        if content and len(content) > 50:
                            seen_urls.append(ad_url) 
                        continue
                    
                    ads_to_analyze.append({
                        "url": ad_url,
                        "content": content[:15000], # Limit content per ad to fit context
                        "site": page.site_name
                    })
                    
                    # Small delay between scrapes
                    time.sleep(2)

            except Exception as e:
                print(f"⚠️ Error harvesting: {e}")

        # --- STEP 3: BATCH ANALYZE ---
        if ads_to_analyze:
            print(f"\n🧠 Sending BATCH analysis for {len(ads_to_analyze)} items to Gemini...")
            
            # Construct a massive prompt
            batch_content = f"I am looking for: {ITEM_NAME}\n\nHere are {len(ads_to_analyze)} advertisements to check:\n\n"
            for i, ad in enumerate(ads_to_analyze):
                batch_content += f"--- AD #{i+1} ({ad['site']}) ---\nURL: {ad['url']}\nCONTENT:\n{ad['content']}\n\n"
            
            batch_content += """
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

            try:
                response_batch = call_gemini(batch_content, BatchProductCheck)
                
                if response_batch and response_batch.parsed:
                    for res in response_batch.parsed.results:
                        if res.found_item:
                            print(f"   ✅ MATCH! {res.item_name}")
                            requests.post(
                                f"https://ntfy.sh/{NTFY_TOPIC}", 
                                data=f"Found: {res.item_name}\n💰 {res.price}\n🔗 {res.url}".encode("utf-8"),
                                headers={
                                    "Title": "Deal Found!", 
                                    "Click": res.url,
                                    "Tags": "loudspeaker"
                                }
                            )
                            found_something_new = True
                        else:
                            print(f"   ❌ {res.item_name} ({res.reasoning})")
                        
                        seen_urls.append(res.url)
                else:
                    print("⚠️ Batch analysis failed or returned empty.")

            except Exception as e:
                print(f"❌ Batch processing error: {e}")

    # --- STEP 4: SAVE ---
    if found_something_new:
        save_history(seen_urls)
        git_commit_changes()
    else:
        print("\n💤 Scan complete. No new matches found.")

if __name__ == "__main__":
    asyncio.run(main())