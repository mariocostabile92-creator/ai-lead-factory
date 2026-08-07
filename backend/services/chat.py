import json
import re
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.store import get_or_create_conversation, save_chat_turn


MODULE_KEYWORDS = {
    "leads": ["cliente", "clienti", "lead", "contatti", "vendere", "azienda", "prospect"],
    "outreach": ["email", "messaggio", "linkedin", "whatsapp", "follow-up", "follow up"],
    "hiring": ["assumere", "assunzione", "candidato", "cv", "colloquio", "dipendente"],
    "documents": ["preventivo", "contratto", "documento", "offerta", "proposta"],
    "operations": ["organizzare", "task", "scadenza", "processo", "operativo", "priorita"],
}

CHAT_SCHEMA = {
    "name": "lead_factory_chat_reply",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "module": {
                "type": "string",
                "enum": ["leads", "outreach", "hiring", "documents", "operations"],
            },
            "reply": {"type": "string"},
            "cta": {"type": "string"},
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
        },
        "required": ["module", "reply", "cta", "suggestions"],
    },
}


def detect_module(message: str) -> str:
    normalized = message.lower()
    scores = {
        module: sum(keyword in normalized for keyword in keywords)
        for module, keywords in MODULE_KEYWORDS.items()
    }
    selected = max(scores, key=scores.get)
    return selected if scores[selected] > 0 else "operations"


def get_recent_messages(db: Session | None, conversation_id: str | None) -> list[dict[str, str]]:
    if db is None or not conversation_id:
        return []

    from backend.models.conversation import ConversationMessage

    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(8)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def build_system_prompt(module: str, business_name: str, sector: str, location: str) -> str:
    focus = {
        "leads": "lead generation, target selection, first contact, conversion",
        "outreach": "sales messaging, follow-up, objection handling, next step",
        "hiring": "recruiting, role definition, interview flow, selection",
        "documents": "commercial documents, proposals, structure, clarity",
        "operations": "priorities, execution, planning, accountability",
    }[module]

    return (
        "You are AI Lead Factory, a sharp and practical business assistant.\n"
        "Your job is to help the user move toward revenue, saved time, or clear next steps.\n"
        "Be direct, concrete, and commercially useful. Avoid generic advice.\n"
        "Always include a clear CTA that tells the user what to do next.\n"
        "If the request is vague, ask one short clarifying question inside the reply.\n"
        "Keep the answer concise: short paragraphs, no fluff.\n"
        f"Current business context: business={business_name}, sector={sector}, location={location}.\n"
        f"Primary focus area: {focus}."
    )


def build_fallback(module: str, business_name: str, sector: str, location: str) -> tuple[str, str, list[str]]:
    if module == "leads":
        reply = (
            f"Ti aiuto a trovare clienti per {business_name}. "
            f"Parti da 20 target molto vicini a {sector} nella zona di {location}, poi scrivi un messaggio breve con un vantaggio chiaro."
        )
        cta = "Vuoi che ti preparo subito i primi 50 target?"
        suggestions = [
            "Scrivi il cliente ideale",
            "Genera la mail iniziale",
            "Prepara il follow-up",
        ]
    elif module == "outreach":
        reply = (
            f"Per {business_name} il messaggio deve essere corto, specifico e orientato al risultato. "
            "Ti conviene aprire con un problema che risolvi e chiudere con una richiesta semplice."
        )
        cta = "Vuoi che ti scriva email, LinkedIn e WhatsApp insieme?"
        suggestions = [
            "Scrivi email di apertura",
            "Crea messaggio LinkedIn",
            "Crea 3 follow-up",
        ]
    elif module == "hiring":
        reply = (
            f"Per assumere bene in {location}, devi prima chiarire ruolo, obiettivo e competenze davvero necessarie per {business_name}."
        )
        cta = "Vuoi che ti preparo l'annuncio e le domande colloquio?"
        suggestions = [
            "Scrivi l'annuncio",
            "Crea le domande",
            "Prepara la griglia valutazione",
        ]
    elif module == "documents":
        reply = (
            f"Per {business_name} posso trasformare una richiesta confusa in un documento ordinato e vendibile. "
            "Conviene partire da obiettivo, condizioni, tempi e prossimo passo."
        )
        cta = "Vuoi che ti prepari una proposta commerciale pronta?"
        suggestions = [
            "Crea un preventivo",
            "Scrivi una proposta",
            "Prepara un contratto base",
        ]
    else:
        reply = (
            f"Mettiamo ordine nel lavoro di {business_name}. "
            "Scegli una priorita, spezzala in tre passi e chiudi oggi la prossima azione utile."
        )
        cta = "Vuoi che organizziamo insieme le prossime 3 azioni?"
        suggestions = [
            "Organizza le priorita",
            "Crea una checklist",
            "Definisci il piano di oggi",
        ]

    return reply, cta, suggestions


def parse_openai_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def extract_output_text(data: dict[str, Any]) -> str | None:
    output_text = data.get("output_text")
    if output_text:
        return output_text

    for item in data.get("output", []):
        for content_item in item.get("content", []):
            if content_item.get("type") == "output_text":
                return content_item.get("text")
            if content_item.get("type") == "text":
                return content_item.get("text")
    return None


def call_openai_model(
    module: str,
    business_name: str,
    sector: str,
    location: str,
    user_message: str,
    history: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None

    messages: list[dict[str, str]] = []
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": settings.openai_model,
        "instructions": build_system_prompt(module, business_name, sector, location),
        "input": messages,
        "temperature": 0.4,
        "text": {
            "format": {
                "type": "json_schema",
                "json_schema": CHAT_SCHEMA,
            }
        },
    }

    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=40.0,
        )
        response.raise_for_status()
        data = response.json()
        output_text = extract_output_text(data)
        if not output_text:
            return None
        return parse_openai_json(output_text)
    except Exception:
        return None


def chat_assistant(payload: ChatRequest, db: Session | None = None) -> ChatResponse:
    module = detect_module(payload.message)
    business = payload.business
    business_name = business.business_name if business else "la tua attivita"
    sector = business.sector if business else "il tuo settore"
    location = business.location if business else "la tua zona"

    conversation = None
    history: list[dict[str, str]] = []
    if db is not None:
        conversation = get_or_create_conversation(db, payload.conversation_id, business)
        history = get_recent_messages(db, conversation.id)
        if not conversation.business_name and business:
            conversation.business_name = business.business_name
            conversation.sector = business.sector
            conversation.location = business.location
            db.commit()

    model_output = call_openai_model(
        module=module,
        business_name=business_name,
        sector=sector,
        location=location,
        user_message=payload.message.strip(),
        history=history,
    )

    if model_output is None:
        reply, cta, suggestions = build_fallback(module, business_name, sector, location)
        model_output = {
            "module": module,
            "reply": reply,
            "cta": cta,
            "suggestions": suggestions,
        }

    response = ChatResponse(
        conversation_id=conversation.id if conversation else payload.conversation_id or "",
        module=model_output["module"],
        reply=model_output["reply"],
        cta=model_output["cta"],
        suggestions=list(model_output["suggestions"]),
    )

    if db is not None and conversation is not None:
        save_chat_turn(
            db,
            conversation=conversation,
            user_message=payload.message.strip(),
            assistant_message=f"{response.reply}\n\nCTA: {response.cta}",
            module=response.module,
        )

    return response
