from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService

class LeadsService(BaseAssistantService):
    module_name = "leads"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        business = payload.business
        return AssistantResponse(
            module=self.module_name,
            title="Ricerca potenziali clienti",
            summary=f"Strategia iniziale per {business.business_name} nel settore {business.sector}.",
            actions=[
                f"Definire il cliente ideale nella zona {business.location}",
                "Individuare elenchi e fonti pubbliche pertinenti",
                "Assegnare priorità ai contatti più compatibili",
                "Preparare il primo contatto personalizzato",
            ],
            output=(
                f"Obiettivo ricevuto: {payload.goal}\n\n"
                "La versione MVP prepara criteri di ricerca, profilo cliente ideale "
                "e piano di contatto. L'acquisizione automatica di dati pubblici sarà "
                "collegata nella fase successiva."
            ),
        )
