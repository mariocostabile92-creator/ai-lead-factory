from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService

class OperationsService(BaseAssistantService):
    module_name = "operations"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        return AssistantResponse(
            module=self.module_name,
            title="Piano operativo",
            summary="L'obiettivo è stato trasformato in una sequenza di attività.",
            actions=[
                "Definire il risultato atteso",
                "Assegnare una priorità",
                "Spezzare il lavoro in attività da massimo 60 minuti",
                "Stabilire responsabile e scadenza",
                "Verificare il risultato",
            ],
            output=(
                f"Obiettivo operativo: {payload.goal}\n\n"
                "1. Raccolta informazioni\n"
                "2. Decisione\n"
                "3. Esecuzione\n"
                "4. Controllo\n"
                "5. Chiusura o nuova azione"
            ),
        )
