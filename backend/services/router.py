from sqlalchemy.orm import Session

from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.factory import LeadFactoryService

SERVICE = LeadFactoryService()


def run_assistant(payload: AssistantRequest, db: Session | None = None) -> AssistantResponse:
    return SERVICE.run(payload, db=db)
