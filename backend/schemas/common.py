from pydantic import BaseModel, Field


class BusinessContext(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    sector: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    target: str = Field(default="", max_length=2000)
    details: str = Field(default="", max_length=2000)

class AssistantRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    business: BusinessContext


class ProspectItem(BaseModel):
    name: str = ""
    phone: str = ""
    website: str = ""
    maps_url: str = ""
    address: str = ""
    rating: str = ""
    source: str = ""
    fit_reason: str = ""
    message: str = ""


class AssistantResponse(BaseModel):
    module: str
    title: str
    summary: str
    actions: list[str]
    output: str
    lead_id: int | None = None
    research: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    search_links: list[str] = Field(default_factory=list)
    prospects: list[ProspectItem] = Field(default_factory=list)
