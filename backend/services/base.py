from backend.schemas.common import AssistantRequest, AssistantResponse

class BaseAssistantService:
    module_name = "generic"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        raise NotImplementedError
