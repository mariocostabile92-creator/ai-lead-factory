import json
import re
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openai_client import call_with_timeout, get_openai_client
from backend.services.store import (
    get_or_create_conversation,
    save_chat_turn,
    update_conversation_response_id,
)


MODULE_KEYWORDS = {
    "leads": ["cliente", "clienti", "lead", "contatti", "vendere", "azienda", "prospect", "ricerca"],
    "outreach": ["email", "messaggio", "linkedin", "whatsapp", "follow-up", "follow up"],
    "hiring": ["assumere", "assunzione", "candidato", "cv", "colloquio", "dipendente"],
    "documents": ["preventivo", "contratto", "documento", "offerta", "proposta"],
    "operations": ["organizzare", "task", "scadenza", "processo", "operativo", "priorita"],
}

CHAT_SCHEMA = {
    "name": "lead_factory_chat_reply",
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
            "needs_clarification": {"type": "boolean"},
            "follow_up_question": {"type": ["string", "null"]},
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "research": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 5,
            },
            "search_links": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 5,
            },
            "draft_title": {"type": "string"},
            "draft": {"type": "string"},
        },
        "required": [
            "module",
            "reply",
            "cta",
            "needs_clarification",
            "follow_up_question",
            "suggestions",
            "research",
            "search_links",
            "draft_title",
            "draft",
        ],
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


def _clean_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _fallback_reply(module: str, message: str, business_name: str, sector: str, location: str) -> dict[str, Any]:
    lower_message = message.lower()
    draft_title = ""
    draft = ""

    if module == "leads":
        search_queries = [
            f"{sector} aziende {location}",
            f"{sector} contatti {location}",
            f"clienti potenziali {sector} {location}",
        ]
        search_links = [f"https://www.google.com/search?q={quote_plus(query)}" for query in search_queries]
        reply = (
            f"Ti aiuto a cercare clienti per {business_name}. "
            f"Partiamo da target reali in {location}, poi costruiamo un primo messaggio e una lista di contatti."
        )
        cta = "Vuoi che cerchi subito una lista di target reali per la tua zona?"
        suggestions = [
            "Cerca aziende target reali",
            "Scrivi il messaggio iniziale",
            "Prepara il follow-up",
        ]
        research = [
            f"Cerca aziende e decision maker nel settore {sector} a {location}",
            "Definisci 3 criteri per qualificare i prospect migliori",
        ]
    elif module == "outreach":
        search_queries = []
        search_links = []
        draft_title = "Bozza email pronta"
        draft = (
            f"Oggetto: una proposta veloce per {business_name}\n\n"
            f"Ciao,\n"
            f"ti scrivo perché sto aiutando aziende nel settore {sector} a ottenere più risposte dai contatti giusti.\n"
            f"Se ti va, ti preparo una bozza concreta pensata per {location} e per il tuo target.\n\n"
            f"Ti va se te la mando?"
        )
        reply = (
            f"Per {business_name} serve un messaggio breve e specifico. "
            "Ti lascio subito una bozza email pronta e, se vuoi, la adatto anche per LinkedIn e WhatsApp."
        )
        cta = "Ti lascio una bozza email pronta e, se vuoi, la trasformo in LinkedIn e WhatsApp."
        suggestions = [
            "Scrivi email di apertura",
            "Crea messaggio LinkedIn",
            "Crea 3 follow-up",
        ]
        research = []
    elif module == "hiring":
        search_queries = []
        search_links = []
        reply = (
            f"Per assumere bene in {location}, dobbiamo chiarire ruolo, obiettivi e competenze davvero utili per {business_name}."
        )
        cta = "Vuoi che ti preparo l'annuncio e le domande colloquio?"
        suggestions = [
            "Scrivi l'annuncio",
            "Crea le domande",
            "Prepara la griglia valutazione",
        ]
        research = []
    elif module == "documents":
        search_queries = []
        search_links = []
        reply = (
            f"Per {business_name} posso trasformare una richiesta confusa in un documento chiaro e vendibile."
        )
        cta = "Vuoi che ti prepari una proposta commerciale pronta?"
        suggestions = [
            "Crea un preventivo",
            "Scrivi una proposta",
            "Prepara un contratto base",
        ]
        research = []
    else:
        search_queries = []
        search_links = []
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
        research = []

    if any(term in lower_message for term in ["tutto", "completo", "ricerca", "cerca", "trova"]):
        cta = "Vuoi che faccia una ricerca reale e ti preparo i target?"
        if module == "leads":
            suggestions[0] = "Cerca aziende target reali"

    needs_clarification = not (business_name and sector and location)
    follow_up_question = (
        "Mi dici settore, zona e cosa vendi?"
        if needs_clarification
        else None
    )

    return {
        "module": module,
        "reply": reply,
        "cta": cta,
        "needs_clarification": needs_clarification,
        "follow_up_question": follow_up_question,
        "suggestions": suggestions,
        "research": research,
        "search_links": search_links if module == "leads" else [],
        "draft_title": draft_title,
        "draft": draft,
    }


def _ensure_search_focus(payload: dict[str, Any], module: str, business_name: str, sector: str, location: str) -> dict[str, Any]:
    fallback = _fallback_reply(module, "", business_name, sector, location)
    payload.setdefault("module", module)
    payload.setdefault("reply", fallback["reply"])
    payload.setdefault("cta", fallback["cta"])
    payload.setdefault("needs_clarification", fallback["needs_clarification"])
    payload.setdefault("follow_up_question", fallback["follow_up_question"])
    payload.setdefault("suggestions", list(fallback["suggestions"]))
    payload.setdefault("research", list(fallback["research"]))
    payload.setdefault("search_links", list(fallback.get("search_links", [])))
    payload.setdefault("draft_title", fallback.get("draft_title", ""))
    payload.setdefault("draft", fallback.get("draft", ""))

    if not payload.get("suggestions"):
        payload["suggestions"] = list(fallback["suggestions"])
    if not payload.get("research") and module in {"leads", "outreach"}:
        payload["research"] = list(fallback["research"])
    if not payload.get("search_links") and module == "leads":
        payload["search_links"] = list(fallback.get("search_links", []))
    if module == "outreach" and not payload.get("draft"):
        payload["draft_title"] = "Bozza email pronta"
        payload["draft"] = (
            f"Oggetto: una proposta veloce per {business_name}\n\n"
            f"Ciao,\n"
            f"ti scrivo perché sto aiutando aziende nel settore {sector} a ottenere più risposte dai contatti giusti.\n"
            f"Se ti va, ti preparo una bozza concreta pensata per {location} e per il tuo target.\n\n"
            f"Ti va se te la mando?"
        )
    if module == "leads":
        suggestions = list(payload.get("suggestions", []))
        if not any("cerca" in suggestion.lower() for suggestion in suggestions):
            suggestions.insert(0, "Cerca aziende target reali")
        payload["suggestions"] = suggestions[:3]
        if "ricerca" not in payload.get("cta", "").lower():
            payload["cta"] = "Vuoi che faccia una ricerca reale e ti preparo i target?"
    return payload


def _call_openai_chat(
    module: str,
    business_name: str,
    sector: str,
    location: str,
    message: str,
    conversation_response_id: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    client = get_openai_client()
    if client is None:
        return None, None

    tools = [{"type": "web_search"}] if module in {"leads", "outreach"} else []
    instructions = (
        "You are AI Lead Factory, a sharp, practical business assistant.\n"
        "Never repeat the same question if the needed context is already present in memory.\n"
        "Advance the conversation by proposing the next best concrete action.\n"
        "If the user asks for clients or sales help, include a research step and real-world search suggestions.\n"
        "If business context is incomplete, ask exactly one short clarifying question and stop there.\n"
        "Keep the tone direct, useful, and conversion oriented.\n"
        f"Current context: business={business_name or 'unknown'}, sector={sector or 'unknown'}, location={location or 'unknown'}.\n"
        f"Primary module: {module}."
    )

    response = call_with_timeout(
        lambda: client.responses.create(
            model="gpt-5",
            input=message,
            instructions=instructions,
            previous_response_id=conversation_response_id or None,
            tools=tools,
            text={
                "format": {
                    "type": "json_schema",
                    "name": CHAT_SCHEMA["name"],
                    "schema": CHAT_SCHEMA["schema"],
                    "strict": True,
                }
            },
        ),
        timeout_seconds=10.0,
    )

    if response is None:
        return None, None

    output_text = getattr(response, "output_text", None)
    if not output_text:
        return None, getattr(response, "id", None)

    try:
        return _clean_json(output_text), getattr(response, "id", None)
    except Exception:
        return None, getattr(response, "id", None)


def chat_assistant(payload: ChatRequest, db: Session | None = None) -> ChatResponse:
    module = detect_module(payload.message)
    business = payload.business
    business_name = business.business_name if business else ""
    sector = business.sector if business else ""
    location = business.location if business else ""

    conversation = None
    if db is not None:
        conversation = get_or_create_conversation(db, payload.conversation_id, business)
        if business:
            conversation.business_name = business.business_name
            conversation.sector = business.sector
            conversation.location = business.location
            db.commit()
        else:
            business_name = conversation.business_name or business_name
            sector = conversation.sector or sector
            location = conversation.location or location

    model_output, response_id = _call_openai_chat(
        module=module,
        business_name=business_name,
        sector=sector,
        location=location,
        message=payload.message.strip(),
        conversation_response_id=(conversation.openai_response_id if conversation else None),
    )

    if model_output is None:
        model_output = _fallback_reply(module, payload.message.strip(), business_name, sector, location)
    else:
        model_output = _ensure_search_focus(model_output, module, business_name, sector, location)

    response = ChatResponse(
        conversation_id=conversation.id if conversation else payload.conversation_id or "",
        module=model_output["module"],
        reply=model_output["reply"],
        cta=model_output["cta"],
        needs_clarification=bool(model_output["needs_clarification"]),
        follow_up_question=model_output["follow_up_question"],
        suggestions=list(model_output["suggestions"]),
        research=list(model_output.get("research", [])),
        search_links=list(model_output.get("search_links", [])),
        draft_title=model_output.get("draft_title", ""),
        draft=model_output.get("draft", ""),
    )

    if db is not None and conversation is not None:
        save_chat_turn(
            db,
            conversation=conversation,
            user_message=payload.message.strip(),
            assistant_message=(
                f"{response.reply}\n\nCTA: {response.cta}"
                + (f"\n\nDRAFT: {response.draft}" if response.draft else "")
            ),
            module=response.module,
        )
        if response_id:
            update_conversation_response_id(db, conversation, response_id)

    return response
