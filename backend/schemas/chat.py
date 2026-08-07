from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    business_name: str = ""
    sector: str = ""
    location: str = ""
    target: str = ""
    details: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    business: ChatContext | None = None
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
    search_links: list[str] = Field(default_factory=list)
    draft_title: str = ""
    draft: str = ""
    context: ChatContext = Field(default_factory=ChatContext)
