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

# --- ⚙️ USER CONFIGURATION -----------------------
ITEM_NAME = "XTZ 12.17 Edge"

TARGET_SITES = ["blocket.se", "tradera.com", "hifitorget.se", "kleinanzeigen.de"]
NTFY_TOPIC = "gemini_alerts_change_me_123" # <--- IMPORTANT: Change this to your actual topic!
HISTORY_FILE = "seen_items.json"
# -------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class SearchURLGenerator(BaseModel):
    search_urls: List[str]

class ProductCheck(BaseModel):
    found_item: bool
    item_name: str
    price: str
    reasoning: str

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
    print(f"🕵️ Agent starting SAFE RUN for: {ITEM_NAME}")
    seen_urls = load_history()
    
    # --- STEP 1: PLAN (Generate URLs) ---
    print(f"🧠 Asking Gemini to generate search URLs...")
    
    prompt_generate = f"""
    I want to buy a "{ITEM_NAME}".
    Generate direct search result URLs for: {', '.join(TARGET_SITES)}.
    
    CRITICAL URL RULES:
    - Blocket: MUST be 'https://www.blocket.se/annonser/hela_sverige?q=...' (include 'annonser'!)
    - Tradera: 'https://www.tradera.com/search?q=...'
    - Kleinanzeigen: 'https://www.kleinanzeigen.de/s-suchanfrage.html?keywords=...'
    
    Return ONLY the list of URLs.
    """
    
    try:
        response_plan = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt_generate,
            config={
                "response_mime_type": "application/json",
                "response_schema": SearchURLGenerator,
            },
        )
    except Exception as e:
        print(f"❌ Plan failed: {e}")
        return
    
    target_urls = response_plan.parsed.search_urls
    print(f"📍 Agent generated {len(target_urls)} paths.")

    found_something_new = False
    
    # --- STEP 2: EXECUTE (Scrape & Analyze) ---
    async with AsyncWebCrawler(verbose=False) as crawler:
        for list_url in target_urls:
            print(f"\n🚜 Harvesting: {list_url}")
            time.sleep(2) # Pause 1

            try:
                result = await crawler.arun(url=list_url)
                if not result.success:
                    print(f"⚠️ Failed to load list page")
                    continue

                candidates = []
                for link in result.links.get("internal", []):
                    href = link.get("href", "")
                    if ("/annons/" in href or "/item/" in href or "/s-anzeige/" in href or "/advert/" in href) and len(href) > 20:
                        candidates.append(href)

                new_candidates = [c for c in set(candidates) if c not in seen_urls]
                
                if not new_candidates:
                    print("   -> No new ads found here.")
                    continue

                print(f"   -> Found {len(new_candidates)} new ads. Checking top 3...")
                
                for ad_url in new_candidates[:3]:
                    # --- PAUSE 2: QUOTA SAFETY ---
                    print("   ⏳ Sleeping 15s to respect AI rate limit...")
                    time.sleep(15) 
                    # -----------------------------

                    print(f"   🔍 Analyzing: {ad_url}")
                    
                    # Blocket Fix: Wait 3s
                    ad_result = await crawler.arun(url=ad_url, wait_until="networkidle", delay_before_return_html=3.0)
                    
                    try:
                        response_analyze = client.models.generate_content(
                            model="gemini-flash-latest",
                            contents=f"""
                            Analyze this webpage:
                            {ad_result.markdown[:10000]}
                            
                            Item to find: {ITEM_NAME}
                            
                            1. Is this specific item for sale EXACTLY what I want? 
                            2. Ignore 'wanted' ads or spare parts.
                            3. Extract the price.
                            """,
                            config={
                                "response_mime_type": "application/json",
                                "response_schema": ProductCheck,
                            },
                        )
                        
                        analysis = response_analyze.parsed
                        
                        if analysis.found_item:
                            print(f"   ✅ MATCH! Sending alert for: {analysis.item_name}")
                            
                            # Emoji Fix: Moved to Tags
                            requests.post(
                                f"https://ntfy.sh/{NTFY_TOPIC}", 
                                data=f"Found: {analysis.item_name}\n💰 {analysis.price}\n🔗 {ad_url}".encode("utf-8"),
                                headers={
                                    "Title": "Deal Found!", 
                                    "Click": ad_url,
                                    "Tags": "loudspeaker"
                                }
                            )
                            found_something_new = True
                        else:
                            print(f"   ❌ REJECTED: {analysis.item_name} ({analysis.reasoning})")
                        
                        seen_urls.append(ad_url)

                    except Exception as ai_error:
                        print(f"   ⚠️ AI Error: {ai_error}")
                        if "429" in str(ai_error):
                            print("   🛑 Stopping checks on this site due to quota.")
                            break

            except Exception as e:
                print(f"⚠️ Error harvesting: {e}")

    # --- STEP 3: SAVE ---
    if found_something_new:
        save_history(seen_urls)
        git_commit_changes()
    else:
        print("\n💤 Scan complete. No new matches found.")

if __name__ == "__main__":
    asyncio.run(main())