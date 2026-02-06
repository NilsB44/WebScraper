# 🕵️ Agentic Web Scraper (Gemini + Crawler4AI)

A high-performance, AI-driven web scraper designed to hunt for specific items across multiple European marketplaces. It leverages **Gemini 2.0/Flash** for intelligent content analysis and **Crawl4AI** for robust web harvesting.

## 🚀 Key Features
- **Intelligent Analysis:** Uses LLMs to verify if an ad matches your exact search criteria (color, model, condition).
- **Multi-Source:** Automatically generates search URLs for Blocket, Tradera, Kleinanzeigen, Hifitorget, eBay DE, DBA, and Finn.no.
- **Smart Throttling:** Built-in delays and quota management for Gemini API limits.
- **Push Notifications:** Instant alerts via [ntfy.sh](https://ntfy.sh).
- **History Tracking:** Remembers seen ads to avoid duplicate notifications.

## 📁 Project Structure
The project follows a modular service-oriented architecture:
- `scraper.py`: The main orchestrator (entry point).
- `src/config.py`: Configuration management via Pydantic Settings.
- `src/models.py`: Shared Pydantic data models for structured AI output.
- `src/services/`:
  - `crawler.py`: Web harvesting logic using Crawl4AI and Requests fallback.
  - `analysis.py`: Gemini API integration and prompt engineering.
  - `notification.py`: ntfy.sh messaging service.
  - `storage.py`: History persistence and Git auto-commit logic.

## 🛠️ Setup & Installation

### 1. Prerequisites
- [uv](https://docs.astral.sh/uv/) installed.
- A Google Gemini API Key.

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd WebScraper

# Sync dependencies (creates virtual environment automatically)
uv sync

# Install Playwright browsers
uv run playwright install --with-deps
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_key_here
ITEM_NAME="XTZ 12.17 Edge Subwoofer"
NTFY_TOPIC=your_secret_topic
```

## 🤖 Usage
Run the scraper using uv:
```bash
uv run scraper.py
```

## ☁️ CI/CD (GitHub Actions)
The scraper is configured to run daily via `.github/workflows/daily_scan.yml`. It automatically commits updated history back to the repository to ensure no duplicate alerts across runs.

---
*Created with ❤️ by Nils & Gemini*
