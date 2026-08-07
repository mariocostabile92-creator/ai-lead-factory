from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat import chat_assistant

router = APIRouter()


@router.post("/respond", response_model=ChatResponse)
def respond(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not settings.enable_public_storage:
        return chat_assistant(payload, db=None)
    return chat_assistant(payload, db=db)
