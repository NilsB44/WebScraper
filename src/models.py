from typing import Optional

from pydantic import BaseModel, Field


class SearchPageSource(BaseModel):
    site_name: str
    search_url: str


class SearchURLGenerator(BaseModel):
    search_pages: list[SearchPageSource]


class CandidateItem(BaseModel):
    """Represents a potential match found on a search result page."""
    url: str
    title: str
    price: str
    reasoning: str
    confidence_score: int = Field(description="0-100 score of how likely this is a match")


class SearchPageAnalysis(BaseModel):
    candidates: list[CandidateItem]


class ProductCheck(BaseModel):
    url: str
    found_item: bool
    item_name: str = Field(description="The clear name of the item for sale")
    price: str = Field(description="The price with currency")
    reasoning: str = Field(description="Brief explanation of why this matches or not")


class BatchProductCheck(BaseModel):
    results: list[ProductCheck]


class AdContent(BaseModel):
    url: str
    content: str
    site: str


class ScrapeTask(BaseModel):
    """Defines a specific scraping job."""
    name: str
    search_query: str
    max_price: Optional[int] = None
    currency: str = "SEK"
    description: str = ""
