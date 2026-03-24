# Project Structure

This document outlines the standard directory structure for the `WebScraper` project.

## Root Directory
- `scraper.py`: Main entry point for the application.
- `requirements.txt`: Python dependencies.
- `README.md`: Project documentation and setup instructions.
- `SECURITY.md`: Security policy and vulnerability reporting.
- `.gitignore`: Files and directories to ignore in Git.

## Source Code (`src/`)
Contains the core application logic, modularized by function.
- `src/config.py`: Configuration and environment variable management using Pydantic.
- `src/models.py`: Data models sharing across services.
- `src/services/`:
    - `analysis.py`: Gemini AI integration logic.
    - `crawler.py`: Web scraping logic (Crawl4AI + Requests).
    - `notification.py`: Notification services (ntfy.sh).
    - `storage.py`: File system and Git operations.
    - `orchestrator.py`: High-level workflow orchestration for the scraper.

## Tests (`tests/`)
- `tests/test_crawler.py`: Unit tests for link detection and crawler logic.
- `tests/test_analysis.py`: Unit tests for query generation and site mapping.
- `tests/test_integration.py`: Integration tests for the full scraping flow.
- `tests/test_scenarios.py`: Edge-case and scenario testing for the orchestrator.
- `tests/test_quota.py`: Script to verify API quotas.
- `tests/check_models.py`: Utility to list available Gemini models.

## DevOps & CI/CD
- `.github/workflows/`: GitHub Actions pipelines for scanning, testing, and reviewing.
- `.devcontainer/`: Configuration for VS Code Dev Containers (Docker-based dev environment).
- `.github/CODEOWNERS`: Defines automatic reviewers for PRs.
- `.github/dependabot.yml`: Configuration for automated dependency updates.
