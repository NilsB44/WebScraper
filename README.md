# 🕵️ Agentic Web Scraper (Gemini + GitHub Actions)

This tool automatically searches the web for specific items (like second-hand subwoofers) and sends a push notification to your phone if it finds a good deal. It runs once a day automatically via GitHub Actions.

## ⚙️ Quick Configuration

### 1. Change What to Search For
Open `scraper.py` and edit this line at the top:
```python
SEARCH_QUERY = "Second hand active subwoofer sale europe site:blocket.se OR site:kleinanzeigen.de"