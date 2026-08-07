from pydantic import BaseModel, Field

class BusinessContext(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    sector: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    details: str = Field(default="", max_length=2000)

class AssistantRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    business: BusinessContext

class AssistantResponse(BaseModel):
    module: str
    title: str
    summary: str
    actions: list[str]
    output: str
