import logging

import requests

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, topic: str):
        self.topic = topic
        self.base_url = f"https://ntfy.sh/{topic}"

    def send_notification(self, message: str, title: str = "Scraper Notification",
                          priority: str = "default", click_url: str | None = None,
                          tags: str | None = None) -> bool:
        """Sends a notification to the configured ntfy topic."""
        headers = {
            "Title": title,
            "Priority": priority
        }
        if click_url:
            headers["Click"] = click_url
        if tags:
            headers["Tags"] = tags

        try:
            response = requests.post(
                self.base_url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            logger.debug(f"Notification sent to {self.topic}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def notify_start(self, item_name: str):
        self.send_notification(
            message=f"Scraper started for {item_name}!",
            title="Scraper Online",
            priority="1"
        )

    def notify_match(self, item_name: str, price: str, url: str):
        self.send_notification(
            message=f"""Found: {item_name}
💰 {price}
🔗 {url}""",
            title="Deal Found!",
            click_url=url,
            tags="loudspeaker,moneybag"
        )
