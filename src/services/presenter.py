import json
import logging
import os
from datetime import datetime
from typing import Any

from src.models import ProductCheck

logger = logging.getLogger(__name__)


class ResultsPresenter:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.json_path = os.path.join(data_dir, "results.json")
        self.md_path = "RESULTS.md"
        self.html_path = "public/index.html"

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs("public", exist_ok=True)

    def save_results(self, new_hits: list[ProductCheck], task_name: str, total_scanned: int = 0) -> None:
        # 1. Load existing JSON
        history = self._load_json()

        # 2. Append new hits if any
        timestamp = datetime.now().isoformat()
        if new_hits:
            for hit in new_hits:
                entry = hit.model_dump()
                entry["task"] = task_name
                entry["timestamp"] = timestamp
                history.append(entry)

        # 3. Save JSON
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        # 4. Generate Views
        self._generate_markdown(history, last_task=task_name, last_count=len(new_hits), total=total_scanned)
        self._generate_html(history, last_task=task_name, last_count=len(new_hits), total=total_scanned)

        if new_hits:
            logger.info(f"💾 Saved {len(new_hits)} new hits to history and updated views.")
        else:
            logger.info("ℹ️ No new hits found, but views updated with latest scan timestamp.")

    def _load_json(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.json_path):
            return []
        try:
            with open(self.json_path, encoding="utf-8") as f:
                from typing import cast

                return cast(list[dict[str, Any]], json.load(f))
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def _generate_markdown(
        self, history: list[dict[str, Any]], last_task: str = "", last_count: int = 0, total: int = 0
    ) -> None:
        # Sort by timestamp desc
        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

        md_content = "# 🛒 Scraper Results\n\n"
        md_content += f"**Last Scan:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if last_task:
            md_content += f"- **Task:** {last_task}\n"
            md_content += f"- **New Hits:** {last_count}\n"
            md_content += f"- **Candidates Checked:** {total}\n\n"

        md_content += "## 🏆 Confirmed Hits\n\n"
        md_content += "| Date | Task | Item | Price | Link | Reasoning |\n"
        md_content += "|---|---|---|---|---|---|\n"

        for item in sorted_history:
            date_str = item.get("timestamp", "")[:10]
            name = item.get("item_name", "N/A")
            price = item.get("price", "N/A")
            url = item.get("url", "#")
            reason = item.get("reasoning", "")
            task = item.get("task", "Unknown")

            md_content += f"| {date_str} | {task} | {name} | {price} | [View]({url}) | {reason} |\n"

        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    def _generate_html(
        self, history: list[dict[str, Any]], last_task: str = "", last_count: int = 0, total: int = 0
    ) -> None:
        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

        rows = ""
        for item in sorted_history:
            rows += f"""
            <tr>
                <td>{item.get("timestamp", "")[:16].replace("T", " ")}</td>
                <td><span class="badge">{item.get("task", "Unknown")}</span></td>
                <td>{item.get("item_name")}</td>
                <td><strong>{item.get("price")}</strong></td>
                <td>{item.get("reasoning")}</td>
                <td><a href="{item.get("url")}" target="_blank" role="button">Open</a></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scraper Results</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <style>
        body {{ padding: 20px; }}
        .badge {{ background: #333; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }}
        .stats {{
            margin-bottom: 2rem;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #333;
        }}
    </style>
</head>
<body>
    <main class="container">
        <h1>🛒 Scraper Dashboard</h1>

        <div class="stats">
            <p><strong>Last Scan:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Status:</strong> {last_task} completed with {last_count} new hits (from {total} candidates).</p>
        </div>

        <h2>🏆 Confirmed Hits</h2>
        <figure>
            <table role="grid">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Task</th>
                        <th>Item</th>
                        <th>Price</th>
                        <th>Reasoning</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </figure>
    </main>
</body>
</html>
"""
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
