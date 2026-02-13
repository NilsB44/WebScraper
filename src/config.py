import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.models import ScrapeTask

# Configure logger
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    gemini_api_key: str = Field(..., description="API Key for Google Gemini")
    
    # Notification
    ntfy_topic: str = Field(
        default="gemini_and_nils_subscribtion_service", description="Topic for ntfy.sh notifications"
    )
    history_file: str = Field(default="seen_items.json", description="File to store seen URLs")

    # Tasks
    tasks: list[ScrapeTask] = [
        ScrapeTask(
            name="XTZ Subwoofer",
            search_query="XTZ 12.17 Edge Subwoofer",
            description="Find high-end subwoofers."
        ),
        ScrapeTask(
            name="Bull Sculpture",
            search_query="Fighting bull sculpture",
            max_price=2000,
            currency="SEK",
            description="Find bull sculptures/statues under 2000 SEK."
        )
    ]

    target_sites: list[str] = Field(
        default=["blocket.se", "tradera.com", "hifitorget.se", "kleinanzeigen.de", "ebay.de", "dba.dk", "finn.no"],
        description="List of sites to search",
    )

    # Git settings
    ci_mode: bool = Field(default=False, alias="CI")
    git_user_name: str = "Scraper Bot"
    git_user_email: str = "bot@github.com"

    # Browser settings
    headless: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


logger.info("Settings loaded")
settings = Settings()  # type: ignore
