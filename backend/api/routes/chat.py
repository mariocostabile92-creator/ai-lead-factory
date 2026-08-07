from fastapi import APIRouter

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat import chat_assistant

router = APIRouter()


@router.post("/respond", response_model=ChatResponse)
def respond(payload: ChatRequest) -> ChatResponse:
    return chat_assistant(payload)
