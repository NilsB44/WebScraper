# 🕷️ WebScraper: Agentic & Modular Intelligence

This roadmap details the evolution of WebScraper from a simple extraction tool into a highly configurable, agentic intelligence system designed to find anomalies, faulty prices, and hidden opportunities across the web.

## 🎯 High-Level Vision
Transform the scraper into a system where a user can simply state: *"Find faulty priced high-end audio equipment on European marketplaces"* and the agent autonomously configures paths, analyzes data for pricing mistakes, and notifies the user.

## Phase 1: Modular Configuration & Multi-Object Scoping
*   **Dynamic Task Schema:** [x] Implement a plugin-based architecture where scraping targets are defined via simple YAML/JSON (Pydantic models).
*   **Multi-Path Traversal:** [x] Enable the scraper to handle multiple paths and object types in a single run.
*   **Agentic Link Analysis:** [x] Implement a "First-Pass" agent that looks at search result lists and uses reasoning to decide which specific links are worth a "Deep-Dive" crawl.
*   **Fuzzy Search Variations:** [x] Use LLM to generate multiple query variations to catch misspelled or differently named items.

## Phase 2: AI Resilience & Self-Healing
*   **Vision-Guided Self-Healing:** [ ] Implement a mechanism to automatically update CSS/XPath selectors using Gemini Vision when scraping fails.
*   **Stateful Extraction:** [x] Use Gemini 2.0 Flash to maintain context and flag "anomalies" or "faulty prices" during extraction.
*   **Semantic Data Normalization:** [x] Automatically map disparate site data into a unified internal model.

## Phase 3: Anomaly Detection & Advanced Features
*   **Market-Relative Analysis:** [ ] Implement logic to compare extracted prices against market averages to identify genuine "mistakes".
*   **Notification Engine Evolution:** [ ] Support advanced filtering for notifications.
*   **Distributed Architecture:** [ ] Prepare the core for distributed, containerized execution.

## 🏗️ Architectural Design Choices
1.  **Modular Tasks:** Each scrape is a `ScrapeTask` object, allowing independent configuration of queries, prices, and fuzzy-logic toggles.
2.  **Two-Tier Analysis:**
    *   *Tier 1 (Link Filtering):* High-speed text analysis of search result pages to identify potential candidates without loading full ad pages.
    *   *Tier 2 (Deep Verification):* Thorough content extraction and verification of selected candidates to ensure high precision and eliminate false positives.
3.  **Resilient Crawling:** `Crawl4AI` with `domcontentloaded` strategy and a `requests` fallback for Schibsted/bot-protected sites ensures maximum data recovery.
4.  **Exponential Backoff & Multi-Model Fallback:** Gemini calls automatically cycle through 2.0-flash, 1.5-flash, and 1.5-pro with jittered delays to respect rate limits and maximize uptime.

---
*Adheres to the global [AI Coding Standards](https://github.com/NilsB44/infra/blob/main/GEMINI.md).*
