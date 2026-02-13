# 🕷️ WebScraper: Agentic & Modular Intelligence

This roadmap details the evolution of WebScraper from a simple extraction tool into a highly configurable, agentic intelligence system designed to find anomalies, faulty prices, and hidden opportunities across the web.

## 🎯 High-Level Vision
Transform the scraper into a system where a user can simply state: *"Find faulty priced high-end audio equipment on European marketplaces"* and the agent autonomously configures paths, analyzes data for pricing mistakes, and notifies the user.

## Phase 1: Modular Configuration & Multi-Object Scoping
*   **Dynamic Task Schema:** [x] Implement a plugin-based architecture where scraping targets (e.g., "GPU Prices", "Real Estate Anomalies") are defined via simple YAML/JSON configurations.
*   **Multi-Path Traversal:** [x] Enable the scraper to handle multiple paths and object types in a single run, maintaining state across disparate marketplace structures.
*   **Agentic Link Analysis:** [x] Implement a "First-Pass" agent that looks at search result lists and uses reasoning to decide which specific links are worth a "Deep-Dive" crawl, saving tokens and bandwidth.

## Phase 2: AI Resilience & Self-Healing
*   **Vision-Guided Self-Healing:** Implement a mechanism to automatically update CSS/XPath selectors when website structures change. When a selector fails, the system captures a screenshot and uses Gemini Vision to identify the new location of the data.
*   **Stateful Extraction:** Use Gemini 2.0 Flash to maintain context of what "normal" data looks like, allowing it to instantly flag "anomalies" or "faulty prices" during extraction.
*   **Semantic Data Normalization:** Automatically map disparate site data (e.g., "Price", "Kostnad", "Pris") into a unified internal model.

## Phase 3: Anomaly Detection & Advanced Features
*   **Market-Relative Analysis:** Implement logic to compare extracted prices against historical data or other sites to identify genuine "mistakes" or "huge discounts."
*   **Notification Engine Evolution:** Support advanced filtering for notifications (e.g., "Only notify if price is >50% below market average").
*   **Strict Typing & Distributed Architecture:** Maintain 100% `mypy` strict coverage and prepare the core for distributed, containerized execution.

---
*Adheres to the global [AI Coding Standards](https://github.com/NilsB44/infra/blob/main/GEMINI.md).*
