from pydantic import BaseModel, Field

from backend.schemas.common import BusinessContext


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    business: BusinessContext | None = None
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    module: str
    reply: str
    cta: str
    needs_clarification: bool = False
    follow_up_question: str | None = None
    suggestions: list[str]
    research: list[str] = Field(default_factory=list)
