import asyncio
import os
import json
import requests
import subprocess
from duckduckgo_search import DDGS  # <--- NEW LIBRARY
from crawl4ai import AsyncWebCrawler
from google import genai
from pydantic import BaseModel

# --- ⚙️ USER CONFIGURATION -----------------------
# TEST QUERY: Broad search on Blocket to verify notifications work
SEARCH_QUERY = 'subwoofer site:blocket.se' 
NTFY_TOPIC = "gemini_alerts_change_me_123" 
HISTORY_FILE = "seen_items.json"
# -------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class ProductCheck(BaseModel):
    found_item: bool
    item_name: str
    price: str
    url: str
    reasoning: str

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 🧠 MEMORY FUNCTIONS ---
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
        subprocess.run(["git", "config", "--global", "user.name", "Scraper Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@github.com"], check=True)
        subprocess.run(["git", "add", HISTORY_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "🤖 Update seen items history"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("💾 History updated and pushed to repo.")
    except Exception as e:
        print(f"⚠️ Could not push history: {e}")

async def main():
    print(f"🕵️ Agent starting DuckDuckGo search for: {SEARCH_QUERY}")
    
    seen_urls = load_history()
    print(f"📚 Memory loaded: {len(seen_urls)} items previously seen.")

    # 1. DISCOVERY PHASE (DuckDuckGo)
    found_urls = []
    try:
        # We use the DDGS library to search. "max_results" replaces "num_results"
        results = DDGS().text(SEARCH_QUERY, max_results=10)
        if results:
            found_urls = [r['href'] for r in results]
    except Exception as e:
        print(f"⚠️ Search failed: {e}")
        return

    # Filter out URLs we have already seen
    new_urls = [url for url in found_urls if url not in seen_urls]
    
    if not new_urls:
        print("💤 No new links found since last run.")
        return

    print(f"🔗 Found {len(new_urls)} NEW potential links.")
    
    found_something_new = False

    # 2. SCRAPING PHASE
    async with AsyncWebCrawler(verbose=True) as crawler:
        for url in new_urls:
            try:
                print(f"Processing: {url}...")
                result = await crawler.arun(url=url)
                
                if not result.success:
                    print(f"⚠️ Failed to load content for {url}")
                    continue

                # 3. ANALYSIS PHASE
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"""
                    Analyze this webpage content:
                    {result.markdown[:15000]}
                    
                    Task: Check if this is a subwoofer for sale.
                    Rules:
                    1. Set 'found_item' to True if it is a subwoofer.
                    2. Ignore 'wanted' ads.
                    3. Extract the price.
                    """,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ProductCheck,
                    },
                )
                
                analysis = response.parsed
                
                # 4. NOTIFICATION PHASE
                if analysis.found_item:
                    print(f"✅ FOUND ONE! {analysis.item_name}")
                    
                    message = f"Found: {analysis.item_name}\n💰 {analysis.price}\n🔗 {analysis.url}"
                    requests.post(
                        f"https://ntfy.sh/{NTFY_TOPIC}", 
                        data=message.encode("utf-8"),
                        headers={"Title": "Subwoofer Alert! 🔊", "Click": analysis.url}
                    )
                    
                    # Add to history so we don't alert again
                    seen_urls.append(url)
                    found_something_new = True
                else:
                    print(f"❌ Not a match: {url}")

            except Exception as e:
                print(f"⚠️ Error on {url}: {e}")

    # 5. SAVE MEMORY
    if found_something_new:
        save_history(seen_urls)
        git_commit_changes()
    else:
        print("Nothing new to save.")

if __name__ == "__main__":
    asyncio.run(main())