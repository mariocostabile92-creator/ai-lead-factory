from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.storage import ConversationHistory
from backend.services.store import get_conversation_history

router = APIRouter()


@router.get("/{conversation_id}", response_model=ConversationHistory)
def history(conversation_id: str, db: Session = Depends(get_db)) -> ConversationHistory:
    return get_conversation_history(db, conversation_id)
