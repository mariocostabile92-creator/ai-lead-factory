from sqlalchemy.orm import Session

from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService
from backend.services.store import save_lead


class LeadFactoryService(BaseAssistantService):
    module_name = "lead_factory"

    def run(self, payload: AssistantRequest, db: Session | None = None) -> AssistantResponse:
        business = payload.business
        business_name = business.business_name.strip() or "la tua attivita"
        sector = business.sector.strip()
        location = business.location.strip()
        details = business.details.strip()
        goal = payload.goal.strip()

        summary = (
            f"Pacchetto commerciale pronto per {business_name} in {sector}."
            f" Strategia pensata per vendere piu velocemente a {location}."
        )

        actions = [
            "Definire il cliente ideale e il trigger d'acquisto",
            "Creare una lista di 50 profili target da cercare",
            "Scrivere email, LinkedIn e WhatsApp pronti all'invio",
            "Preparare follow-up, obiezioni e secondo contatto",
        ]

        output = (
            f"# AI Lead Factory\n\n"
            f"Obiettivo inserito: {goal}\n\n"
            f"Attivita: {business_name}\n"
            f"Settore: {sector}\n"
            f"Zona: {location}\n\n"
            f"## Pacchetto pronto\n"
            f"- 50 profili target da cercare nel mercato di riferimento\n"
            f"- Email iniziale personalizzata\n"
            f"- Messaggio LinkedIn breve\n"
            f"- Messaggio WhatsApp di apertura\n"
            f"- Follow-up dopo 3 giorni\n"
            f"- Follow-up finale dopo 7 giorni\n\n"
            f"## Angolo commerciale suggerito\n"
            f"{details or 'Parti da un messaggio semplice, diretto e orientato al risultato.'}\n\n"
            f"## Esempio email\n"
            f"Oggetto: Una proposta veloce per aumentare le richieste da clienti interessati\n\n"
            f"Ciao, lavoro con realta come {business_name} e sto aiutando aziende di {sector} "
            f"a trasformare l'interesse in contatti reali. "
            f"Se ti va, ti preparo un primo pacchetto personalizzato per {location}.\n\n"
            f"## Prossimo passo\n"
            f"Invia questo pacchetto al cliente, verifica la risposta e poi crea una versione automatizzata."
        )

        result = AssistantResponse(
            module=self.module_name,
            title="Pacchetto commerciale pronto",
            summary=summary,
            actions=actions,
            output=output,
        )

        if db is not None:
            lead = save_lead(db, payload, result)
            result.lead_id = lead.id

        return result
