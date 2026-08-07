from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.router import run_assistant

router = APIRouter()

@router.post("/run", response_model=AssistantResponse)
def run(payload: AssistantRequest, db: Session = Depends(get_db)) -> AssistantResponse:
    return run_assistant(payload, db=db)
