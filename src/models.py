from pydantic import BaseModel, Field


class SearchPageSource(BaseModel):
    site_name: str
    search_url: str


class SearchURLGenerator(BaseModel):
    search_pages: list[SearchPageSource]


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
