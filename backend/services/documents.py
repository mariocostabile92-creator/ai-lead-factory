from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService

class DocumentsService(BaseAssistantService):
    module_name = "documents"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        b = payload.business
        return AssistantResponse(
            module=self.module_name,
            title="Bozza documento",
            summary="Struttura iniziale generata dai dati inseriti.",
            actions=[
                "Controllare dati aziendali e destinatario",
                "Inserire condizioni economiche",
                "Aggiungere scadenze e validità",
                "Far verificare i documenti legali da un professionista",
            ],
            output=(
                f"{b.business_name}\n"
                f"Settore: {b.sector}\n"
                f"Zona: {b.location}\n\n"
                f"Oggetto: {payload.goal}\n\n"
                "Premessa\nDescrizione del servizio\nCondizioni economiche\n"
                "Tempi di esecuzione\nValidità della proposta\nFirma"
            ),
        )
