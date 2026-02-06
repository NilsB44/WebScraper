import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    gemini_api_key: str = Field(..., description="API Key for Google Gemini")
    item_name: str = Field(default="XTZ 12.17 Edge Subwoofer", description="Name of the item to search for")
    ntfy_topic: str = Field(default="gemini_and_nils_subscribtion_service", description="Topic for ntfy.sh notifications")
    history_file: str = Field(default="seen_items.json", description="File to store seen URLs")
    
    target_sites: List[str] = Field(
        default=[
            "blocket.se", 
            "tradera.com", 
            "hifitorget.se", 
            "kleinanzeigen.de", 
            "ebay.de", 
            "dba.dk",
            "finn.no"
        ],
        description="List of sites to search"
    )

    # Git settings
    ci_mode: bool = Field(default=False, alias="CI")
    git_user_name: str = "Scraper Bot"
    git_user_email: str = "bot@github.com"

    # Browser settings
    headless: bool = True
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

print("DEBUG: Settings loaded") # Bad: unnecessary print in a library-style file
settings = Settings()
