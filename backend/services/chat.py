from backend.schemas.chat import ChatRequest, ChatResponse


MODULE_KEYWORDS = {
    "leads": ["cliente", "clienti", "lead", "contatti", "vendere", "azienda", "prospect"],
    "outreach": ["email", "messaggio", "linkedin", "whatsapp", "follow-up", "follow up"],
    "hiring": ["assumere", "assunzione", "candidato", "cv", "colloquio", "dipendente"],
    "documents": ["preventivo", "contratto", "documento", "offerta", "proposta"],
    "operations": ["organizzare", "task", "scadenza", "processo", "operativo", "priorita"],
}


def detect_module(message: str) -> str:
    normalized = message.lower()
    scores = {
        module: sum(keyword in normalized for keyword in keywords)
        for module, keywords in MODULE_KEYWORDS.items()
    }
    selected = max(scores, key=scores.get)
    return selected if scores[selected] > 0 else "operations"


def build_reply(payload: ChatRequest, module: str) -> ChatResponse:
    business = payload.business
    business_name = business.business_name if business else "la tua attività"
    sector = business.sector if business else "il tuo settore"
    location = business.location if business else "la tua zona"
    message = payload.message.strip()

    if module == "leads":
        reply = (
            f"Ti aiuto a trovare clienti per {business_name}. "
            f"La mossa più utile ora è definire chi compra davvero in {sector} e fare una lista di target a {location}. "
            "Poi costruisci un messaggio breve con un beneficio chiaro e un invito semplice."
        )
        suggestions = [
            "Genera 50 lead target",
            "Scrivi l'email iniziale",
            "Prepara il follow-up",
        ]
    elif module == "outreach":
        reply = (
            f"Posso scrivere il messaggio giusto per {business_name}. "
            "Tienilo breve, specifico e orientato al risultato. "
            "Se vuoi, ti preparo una sequenza con email, LinkedIn, WhatsApp e follow-up."
        )
        suggestions = [
            "Scrivi una mail di apertura",
            "Prepara un messaggio LinkedIn",
            "Crea 3 follow-up",
        ]
    elif module == "hiring":
        reply = (
            f"Per assumere meglio in {location}, conviene descrivere ruolo, obiettivi e competenze davvero necessarie. "
            f"Per {business_name} posso preparare annuncio, domande colloquio e checklist di selezione."
        )
        suggestions = [
            "Scrivi l'annuncio",
            "Crea le domande colloquio",
            "Prepara la griglia di valutazione",
        ]
    elif module == "documents":
        reply = (
            f"Per {business_name} posso trasformare la richiesta in un documento ordinato e più professionale. "
            "Il trucco è partire da obiettivo, condizioni, tempi e prossimo passo."
        )
        suggestions = [
            "Crea un preventivo",
            "Scrivi una proposta",
            "Prepara un contratto base",
        ]
    else:
        reply = (
            f"Ti aiuto a mettere ordine nel lavoro di {business_name}. "
            "Parti da una sola priorità, spezzala in passi piccoli e chiudi un'azione utile oggi. "
            "Se vuoi, trasformo anche il tuo obiettivo in una sequenza operativa chiara."
        )
        suggestions = [
            "Organizza le prossime 3 azioni",
            "Crea una checklist",
            "Definisci la priorità di oggi",
        ]

    if any(term in message.lower() for term in ["tutto", "aiuta tutto", "fare tutto", "completo"]):
        reply += " Posso anche fare da centrale operativa: clienti, messaggi, documenti e organizzazione nello stesso flusso."

    return ChatResponse(module=module, reply=reply, suggestions=suggestions)


def chat_assistant(payload: ChatRequest) -> ChatResponse:
    module = detect_module(payload.message)
    return build_reply(payload, module)
