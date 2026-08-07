from pydantic import BaseModel, Field

from backend.schemas.common import BusinessContext


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    business: BusinessContext | None = None


class ChatResponse(BaseModel):
    module: str
    reply: str
    suggestions: list[str]
