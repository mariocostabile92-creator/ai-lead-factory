from fastapi import APIRouter

from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.router import run_assistant

router = APIRouter()

@router.post("/run", response_model=AssistantResponse)
def run(payload: AssistantRequest) -> AssistantResponse:
    return run_assistant(payload)
