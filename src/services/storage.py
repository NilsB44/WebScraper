import json
import logging
import os
import subprocess
from typing import List

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[str]:
        """Loads the history of seen URLs."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"[WARNING] History file {self.file_path} corrupted. Starting fresh.")
                return []
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                return []
        return []

    def save(self, history: List[str]):
        """Saves the history of seen URLs."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

class GitManager:
    def __init__(self, file_path: str, user_name: str, user_email: str):
        self.file_path = file_path
        self.user_name = user_name
        self.user_email = user_email

    def _run_git_command(self, args: List[str]) -> bool:
        try:
            subprocess.run(["git"] + args, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: git {' '.join(args)}\nError: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected git error: {e}")
            return False

    def has_changes(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", self.file_path], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def commit_and_push(self, message: str):
        if not self.has_changes():
            logger.info("No changes to commit.")
            return

        logger.info("[GIT] Committing changes to Git...")
        # Configure local user if not present (optional, but good for CI)
        self._run_git_command(["config", "user.name", self.user_name])
        self._run_git_command(["config", "user.email", self.user_email])
        
        if self._run_git_command(["add", self.file_path]):
            if self._run_git_command(["commit", "-m", message]):
                if self._run_git_command(["push"]):
                    logger.info("[GIT] History updated and pushed to repo.")
                else:
                    logger.error("❌ Failed to push changes.")
            else:
                logger.error("❌ Failed to commit changes.")
        else:
            logger.error("❌ Failed to stage changes.")