from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService

class HiringService(BaseAssistantService):
    module_name = "hiring"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        b = payload.business
        return AssistantResponse(
            module=self.module_name,
            title="Piano di assunzione",
            summary=f"Prima struttura per cercare personale in {b.location}.",
            actions=[
                "Definire ruolo, esperienza e disponibilità",
                "Preparare un annuncio chiaro",
                "Selezionare i portali e i canali locali",
                "Creare una griglia semplice di valutazione",
            ],
            output=(
                f"{b.business_name} cerca una nuova figura nel settore {b.sector}.\n\n"
                f"Obiettivo: {payload.goal}\n\n"
                "Descrivere responsabilità, requisiti obbligatori, orari, sede, "
                "inquadramento e modalità di candidatura."
            ),
        )
