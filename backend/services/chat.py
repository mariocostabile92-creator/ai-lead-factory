import json
import re
import unicodedata
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
    "leads": [
        "cliente",
        "clienti",
        "lead",
        "contatti",
        "vendere",
        "azienda",
        "aziende",
        "prospect",
        "ricerca",
        "cerca",
        "trova",
        "target",
        "lista",
        "nominativi",
        "potenziali",
    ],
    "outreach": [
        "email",
        "mail",
        "messaggio",
        "linkedin",
        "whatsapp",
        "follow-up",
        "follow up",
        "scrivi",
        "bozza",
        "oggetto",
    ],
    "hiring": ["assumere", "assunzione", "candidato", "cv", "colloquio", "dipendente"],
    "documents": ["preventivo", "contratto", "documento", "offerta", "proposta"],
    "operations": ["organizzare", "task", "scadenza", "processo", "operativo", "priorita", "checklist", "piano"],
}

OUTREACH_FORMAT_KEYWORDS = {
    "email": ["email", "mail", "messaggio email", "oggetto"],
    "linkedin": ["linkedin", "linked in", "messaggio linkedin", "dm"],
    "follow_up": ["follow-up", "follow up", "rinvito", "sollecito", "secondo messaggio"],
}

MODULE_PRIORITY = {
    "leads": [
        "cerca aziende",
        "trova clienti",
        "trova aziende",
        "aziende target",
        "target reali",
        "nuovi clienti",
        "lista contatti",
        "lista lead",
    ],
    "outreach": [
        "scrivi email",
        "scrivimi email",
        "messaggio linkedin",
        "messaggio whatsapp",
        "email di apertura",
        "follow up",
        "follow-up",
    ],
    "documents": ["crea preventivo", "scrivi proposta", "contratto base"],
    "hiring": ["annuncio lavoro", "domande colloquio", "assumere"],
    "operations": ["organizza", "checklist", "piano di oggi", "priorita"],
}

LOCATION_PATTERNS = [
    r"\b(?:a|in|su|zona|vicino a|nei pressi di)\s+([a-zA-ZÀ-ÿ' -]{2,60})",
]

TARGET_PATTERNS = [
    r"\b(?:azienda|aziende|attivita|negozio|negozi|cliente|clienti|lead|prospect)\s+(?:di|da|per|nel settore)\s+([a-zA-ZÀ-ÿ' -]{3,80})",
    r"\b(?:di|da|per)\s+([a-zA-ZÀ-ÿ' -]{3,80})",
]

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


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def detect_module(message: str) -> str:
    normalized = normalize_text(message)
    for module, phrases in MODULE_PRIORITY.items():
        if any(phrase in normalized for phrase in phrases):
            return module

    scores = {
        module: sum(keyword in normalized for keyword in keywords)
        for module, keywords in MODULE_KEYWORDS.items()
    }
    selected = max(scores, key=scores.get)
    return selected if scores[selected] > 0 else "operations"


def detect_outreach_format(message: str) -> str:
    normalized = normalize_text(message)
    scores = {
        intent: sum(keyword in normalized for keyword in keywords)
        for intent, keywords in OUTREACH_FORMAT_KEYWORDS.items()
    }
    selected = max(scores, key=scores.get)
    return selected if scores[selected] > 0 else "email"


def _clean_extracted_value(value: str) -> str:
    cleaned = normalize_text(value)
    cleaned = re.sub(
        r"\b(ok|ho|bisogno|devo|voglio|vorrei|trovare|cercare|una|un|delle|degli|dei|le|gli|i|il|la)\b",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"[^a-z0-9à-ÿ' -]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" -")


def _infer_context_from_message(message: str, sector: str, location: str, target: str) -> tuple[str, str, str]:
    normalized = normalize_text(message)
    inferred_sector = sector.strip()
    inferred_location = location.strip()
    inferred_target = target.strip()

    if not inferred_location:
        for pattern in LOCATION_PATTERNS:
            match = re.search(pattern, normalized)
            if match:
                possible_location = _clean_extracted_value(match.group(1))
                if possible_location and possible_location not in {"azienda", "aziende", "cliente", "clienti"}:
                    inferred_location = possible_location.title()
                    break

    if not inferred_target:
        for pattern in TARGET_PATTERNS:
            match = re.search(pattern, normalized)
            if match:
                possible_target = _clean_extracted_value(match.group(1))
                if possible_target and possible_target != inferred_location.lower():
                    inferred_target = possible_target
                    break

    if not inferred_target:
        compact = re.sub(
            r"\b(ok|ho|bisogno|devo|voglio|vorrei|mi|serve|servono|trovare|cercare|trova|cerca|nuovi|clienti|lead|prospect|azienda|aziende|attivita|di|da|per|un|una|il|la|i|le)\b",
            " ",
            normalized,
        )
        compact = _clean_extracted_value(compact)
        if compact:
            inferred_target = compact

    if not inferred_sector and inferred_target:
        inferred_sector = inferred_target

    return inferred_sector, inferred_location, inferred_target


def _clean_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _build_outreach_copy(
    business_name: str,
    sector: str,
    location: str,
    target: str,
    intent: str,
) -> dict[str, str | list[str]]:
    target_focus = target or f"aziende nel settore {sector}"

    if intent == "linkedin":
        return {
            "draft_title": "Messaggio LinkedIn pronto",
            "draft": chr(10).join([
                f"Ciao, ti scrivo su LinkedIn perché lavoro con realtà nel settore {sector} a {location} e sto aiutando aziende come {business_name} a ottenere più risposte dai contatti giusti.",
                "Ti lascio due righe concrete da inviare come messaggio LinkedIn.",
            ]),
            "cta": "Vuoi che lo adatti in tono più diretto o più commerciale?",
            "suggestions": [
                "Scrivi un messaggio LinkedIn",
                "Crea una seconda variante LinkedIn",
                "Prepara il follow-up",
            ],
        }

    if intent == "follow_up":
        return {
            "draft_title": "Follow-up pronto",
            "draft": chr(10).join([
                "Ciao, ti riscrivo solo per capire se hai avuto modo di vedere il messaggio precedente.",
                "Se ti va, ti mando un esempio più concreto e ti lascio tutto già pronto da valutare.",
            ]),
            "cta": "Vuoi che ti preparo anche il secondo e terzo follow-up?",
            "suggestions": [
                "Crea il primo follow-up",
                "Crea il secondo follow-up",
                "Crea il terzo follow-up",
            ],
        }

    return {
        "draft_title": "Bozza email pronta",
        "draft": chr(10).join([
            f"Oggetto: una proposta veloce per {business_name}",
            "",
            "Ciao,",
            f"ti scrivo perché sto aiutando aziende nel settore {sector} a ottenere più risposte dai contatti giusti.",
            f"Se ti va, ti preparo una bozza concreta pensata per {location} e per il tuo target.",
            "",
            "Ti va se te la mando?",
        ]),
        "cta": "Vuoi che ti scriva anche la versione email completa e il follow-up?",
        "suggestions": [
            "Scrivi email di apertura",
            "Crea messaggio LinkedIn",
            "Crea 3 follow-up",
        ],
    }


def _build_contextual_outreach_copy(
    business_name: str,
    sector: str,
    location: str,
    target: str,
    intent: str,
) -> dict[str, str | list[str]]:
    target_focus = target or f"aziende nel settore {sector}"
    if intent == "linkedin":
        return {
            "draft_title": "Messaggio LinkedIn pronto",
            "draft": chr(10).join([
                f"Ciao, ti scrivo su LinkedIn perche ho visto che lavorate su un tema vicino a {target_focus}.",
                f"Noi di {business_name} aiutiamo realta nel settore {sector} a trasformare contatti interessati in richieste concrete.",
                "Ti va se ti mando una proposta molto breve per capire se puo avere senso parlarne?",
            ]),
            "cta": "Vuoi che lo adatti in tono piu diretto o piu commerciale?",
            "suggestions": [
                "Crea una variante piu breve",
                "Scrivi email di apertura",
                "Prepara il follow-up",
            ],
        }

    if intent == "follow_up":
        return {
            "draft_title": "Follow-up pronto",
            "draft": chr(10).join([
                "Ciao, ti riscrivo solo per capire se hai avuto modo di vedere il messaggio precedente.",
                f"Te lo chiedo perche stiamo lavorando con {target_focus} a {location} e credo che ci sia un possibile aggancio concreto.",
                "Se non e il momento giusto nessun problema; in alternativa ti mando due righe molto pratiche e valuti con calma.",
            ]),
            "cta": "Vuoi che ti preparo anche secondo e terzo follow-up?",
            "suggestions": [
                "Crea secondo follow-up",
                "Crea terzo follow-up",
                "Riscrivi piu diretto",
            ],
        }

    return {
        "draft_title": "Bozza email pronta",
        "draft": chr(10).join([
            f"Oggetto: proposta veloce per {location}",
            "",
            "Ciao,",
            f"ti scrivo perche sto cercando realta come la tua tra {target_focus}.",
            f"{business_name} lavora nel settore {sector} e puo aiutarti a ottenere piu richieste dai contatti giusti.",
            "Se ha senso, ti mando una proposta molto breve e concreta.",
            "",
            "Ti va se te la mando?",
        ]),
        "cta": "Vuoi che trasformo questa email anche in messaggio LinkedIn e follow-up?",
        "suggestions": [
            "Crea messaggio LinkedIn",
            "Crea 3 follow-up",
            "Rendila piu commerciale",
        ],
    }


def _search_queries(sector: str, location: str, target: str) -> list[str]:
    target_focus = target or sector
    return [
        f"{target_focus} {location}",
        f"aziende {sector} {location}",
        f"contatti decision maker {target_focus} {location}",
        f"site:linkedin.com/company {target_focus} {location}",
        f"Google Maps {target_focus} {location}",
    ]


def _fallback_reply(
    module: str,
    message: str,
    business_name: str,
    sector: str,
    location: str,
    target: str,
    details: str,
) -> dict[str, Any]:
    lower_message = normalize_text(message)
    draft_title = ""
    draft = ""
    business_label = business_name or "la tua attivita"

    if module == "leads":
        target_focus = target or f"aziende nel settore {sector}" if sector else "aziende target"
        search_queries = _search_queries(sector, location, target)
        search_links = [f"https://www.google.com/search?q={quote_plus(query)}" for query in search_queries]
        if location:
            next_step = "Ti preparo una ricerca utilizzabile: fonti da aprire, criteri di selezione e prossimo messaggio."
            cta = "Apri i link, salva 10 aziende buone e poi ti preparo messaggi personalizzati."
        else:
            next_step = "Ho capito cosa cerchi; mi manca solo la zona per evitare risultati a caso."
            cta = "Scrivimi la citta o provincia e parto con una ricerca mirata."
        reply = (
            f"Ok, cerchiamo prospect reali per {business_label}. "
            f"Target capito: {target_focus}. "
            f"Zona: {location or 'da definire'}. "
            f"{next_step}"
        )
        suggestions = [
            f"Cerca {target_focus} nella mia zona",
            "Scrivi email per questi target",
            "Crea follow-up per questi target",
        ]
        research = [
            f"Cerca aziende che corrispondono a: {target_focus}",
            f"Priorita geografica: {location}",
            "Fonti utili: Google Maps, LinkedIn, registri imprese, associazioni locali",
            "Criteri: settore coerente, dimensione azienda, referente raggiungibile, segnale di bisogno",
        ]
    elif module == "outreach":
        search_queries = []
        search_links = []
        intent = detect_outreach_format(message)
        copy = _build_contextual_outreach_copy(business_name, sector, location, target, intent)
        draft_title = str(copy["draft_title"])
        draft = str(copy["draft"])
        reply = (
            f"Chiaro. Per {business_name} preparo una bozza {intent.replace('_', ' ')} agganciata al target reale, non generica."
        )
        cta = str(copy["cta"])
        suggestions = list(copy["suggestions"])
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

    if module != "leads" and any(term in lower_message for term in ["tutto", "completo", "ricerca", "cerca", "trova"]):
        cta = "Vuoi che faccia una ricerca reale e ti preparo i target?"

    missing = []
    if not sector and not target:
        missing.append("settore o tipo di azienda")
    if not location:
        missing.append("zona")
    needs_clarification = bool(missing)
    follow_up_question = f"Mi manca solo: {', '.join(missing)}." if missing else None

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


def _ensure_search_focus(
    payload: dict[str, Any],
    module: str,
    business_name: str,
    sector: str,
    location: str,
    target: str,
    details: str,
    message: str,
) -> dict[str, Any]:
    fallback = _fallback_reply(module, "", business_name, sector, location, target, details)
    intent = detect_outreach_format(message) if module == "outreach" else ""
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
    if module == "outreach":
        copy = _build_contextual_outreach_copy(business_name, sector, location, target, intent)
        payload["draft_title"] = str(copy["draft_title"])
        payload["draft"] = str(copy["draft"])
        payload["cta"] = str(copy["cta"])
        payload["suggestions"] = list(copy["suggestions"])
    if module == "leads":
        suggestions = list(payload.get("suggestions", []))
        if not any("cerca" in suggestion.lower() for suggestion in suggestions):
            suggestions.insert(0, "Cerca aziende target reali")
        payload["suggestions"] = suggestions[:3]
        if "ricerca" not in payload.get("cta", "").lower() and "link" not in payload.get("cta", "").lower():
            payload["cta"] = fallback["cta"]
    return payload

def _call_openai_chat(
    module: str,
    business_name: str,
    sector: str,
    location: str,
    target: str,
    details: str,
    message: str,
    conversation_response_id: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    client = get_openai_client()
    if client is None:
        return None, None

    tools = [{"type": "web_search"}] if module in {"leads", "outreach"} else []
    instructions = (
        "You are AI Lead Factory, a sharp, practical business assistant.\n"
        "Classify the user's real intent before answering: lead research, outreach copy, documents, hiring, or operations.\n"
        "Never repeat the same question if the needed context is already present in memory.\n"
        "Infer sector, target, and partial intent from the user's wording. If the user says 'erboristeria', treat it as the target/sector.\n"
        "Advance the conversation by proposing the next best concrete action.\n"
        "If the user asks to find clients, companies, prospects, targets, contacts, or says 'cerca aziende target reali', answer as lead research.\n"
        "For lead research, include concrete search sources, qualification criteria, and useful search links.\n"
        "If the user asks to write an email, LinkedIn message, WhatsApp, or follow-up, return usable copy in draft_title and draft.\n"
        "If only the location is missing, ask only for location. If only the sector/target is missing, ask only for that.\n"
        "Keep the tone direct, useful, and conversion oriented. Avoid generic productivity advice unless the user asks for operations.\n"
        f"Current context: business={business_name or 'unknown'}, sector={sector or 'unknown'}, location={location or 'unknown'}.\n"
        f"Target to research/sell to: {target or 'unknown'}.\n"
        f"Extra business details: {details or 'none'}.\n"
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
    target = business.target if business else ""
    details = business.details if business else ""
    sector, location, target = _infer_context_from_message(payload.message, sector, location, target)

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
        target=target,
        details=details,
        message=payload.message.strip(),
        conversation_response_id=(conversation.openai_response_id if conversation else None),
    )

    if model_output is None:
        model_output = _fallback_reply(module, payload.message.strip(), business_name, sector, location, target, details)
    else:
        model_output = _ensure_search_focus(
            model_output,
            module,
            business_name,
            sector,
            location,
            target,
            details,
            payload.message.strip(),
        )

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

