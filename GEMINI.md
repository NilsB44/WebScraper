# AI Coding Standards

All development in this repository MUST adhere to the global standards defined in the infrastructure coordinator:

👉 **[Global Standards (infra/GEMINI.md)](https://github.com/NilsB44/infra/blob/main/GEMINI.md)**

## Local Instructions
- Always run local tests before committing.
- Use `uv` for dependency management if applicable.
- Follow the architectural patterns outlined in `ROADMAP.md`.

## Project-Specific Design Choices

### 1. Robust Content Fetching
- **Content Limit:** The scraper is configured to fetch up to **150,000 characters** of HTML/Markdown content (`MAX_CONTENT_LENGTH` in `src/services/crawler.py`). This is crucial for handling modern, heavy e-commerce sites (SPA, hydration) where search results might be buried deep in the DOM.
- **LLM Context:** The Gemini Analyzer prompt is synchronized to accept this larger context window (up to 150k chars) to ensure no candidates are missed due to truncation.

### 2. Results Presentation
- **Persistence:** Verified hits are saved to `data/results.json` for machine readability and historical tracking.
- **Visualization:** 
    - A `RESULTS.md` file is automatically generated/updated in the root directory, providing a Git-native view of the latest findings.
    - A `public/index.html` is generated as a simple, standalone HTML dashboard (using Pico.css) for an enhanced viewing experience.
- **Notification:** Real-time notifications via `ntfy.sh` are sent for immediate awareness.

### 3. Agentic Workflow
- **Search:** Fuzzy search query generation is used to cover variations.
- **Analysis:** Uses a two-stage agentic process:
    1.  **Broad Scan:** Analyzes search listing pages to identify potential candidates.
    2.  **Deep Dive:** Visits individual item pages for detailed verification before alerting.
