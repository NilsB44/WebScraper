import asyncio
import os
import json
import requests
import subprocess
from googlesearch import search
from crawl4ai import AsyncWebCrawler
from google import genai
from pydantic import BaseModel
from datetime import datetime

# --- ⚙️ USER CONFIGURATION -----------------------
# Specific search for XTZ 12.17 Edge across major EU sites
SEARCH_QUERY = 'intitle:"XTZ 12.17 Edge" (site:blocket.se OR site:tradera.com OR site:kleinanzeigen.de OR site:ebay.de OR site:hifitorget.se OR site:marktplaats.nl)'
NTFY_TOPIC = "gemini_alerts_change_me_123" # <--- MAKE SURE THIS IS YOUR TOPIC!
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
    """Commits the updated history file back to the repo"""
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
    print(f"🕵️ Agent starting search for: {SEARCH_QUERY}")
    
    seen_urls = load_history()
    print(f"📚 Memory loaded: {len(seen_urls)} items previously seen.")

    # 1. DISCOVERY PHASE
    try:
        # Search for more results (10) since we are filtering specifically
        found_urls = list(search(SEARCH_QUERY, num_results=10, advanced=True))
    except Exception as e:
        print(f"⚠️ Search failed: {e}")
        return

    # Filter out URLs we have already seen
    new_urls = [r.url for r in found_urls if r.url not in seen_urls]
    
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
                    continue

                # 3. ANALYSIS PHASE
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"""
                    Analyze this webpage: {result.markdown[:15000]}
                    
                    Target Item: "XTZ 12.17 Edge" subwoofer.
                    Rules:
                    1. MUST be the specific "Edge" model (not the old 12.17).
                    2. MUST be for sale (ignore 'wanted' ads).
                    3. Extract the price if visible.
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
                        headers={"Title": "XTZ Found! 🔊", "Click": analysis.url}
                    )
                    
                    # Add to history so we don't alert again
                    seen_urls.append(url)
                    found_something_new = True
                else:
                    print("❌ Not a match.")
                    # Optional: Add non-matches to history too so we don't check them again?
                    # For now, we only block IF we notified, but you can uncomment below to block everything checked
                    # seen_urls.append(url) 

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