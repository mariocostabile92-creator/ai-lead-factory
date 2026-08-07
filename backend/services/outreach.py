from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService

class OutreachService(BaseAssistantService):
    module_name = "outreach"

    def run(self, payload: AssistantRequest) -> AssistantResponse:
        b = payload.business
        message = (
            f"Buongiorno, sono di {b.business_name}. "
            f"Aiutiamo aziende della zona di {b.location} con servizi nel settore "
            f"{b.sector}. Ho visto la vostra attività e credo possa esserci spazio "
            "per una collaborazione concreta. Possiamo sentirci per 10 minuti?"
        )
        return AssistantResponse(
            module=self.module_name,
            title="Messaggio commerciale pronto",
            summary="Bozza breve, diretta e personalizzabile.",
            actions=[
                "Verificare il nome del destinatario",
                "Aggiungere un riferimento specifico all'azienda",
                "Inviare un follow-up dopo 3 giorni",
            ],
            output=message,
        )
