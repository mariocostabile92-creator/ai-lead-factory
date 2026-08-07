from datetime import datetime

from pydantic import BaseModel


class LeadSummary(BaseModel):
    id: int
    business_name: str
    sector: str
    location: str
    title: str
    module: str
    created_at: datetime


class ConversationMessageItem(BaseModel):
    id: int
    role: str
    content: str
    module: str
    created_at: datetime


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: list[ConversationMessageItem]
