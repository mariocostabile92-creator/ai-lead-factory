from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.factory import LeadFactoryService

SERVICE = LeadFactoryService()


def run_assistant(payload: AssistantRequest) -> AssistantResponse:
    return SERVICE.run(payload)
