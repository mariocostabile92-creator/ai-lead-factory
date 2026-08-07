from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat import chat_assistant

router = APIRouter()


@router.post("/respond", response_model=ChatResponse)
def respond(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return chat_assistant(payload, db=db)
