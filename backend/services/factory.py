import json
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService
from backend.services.openai_client import get_openai_client
from backend.services.store import save_lead


PACKAGE_SCHEMA = {
    "name": "lead_factory_package",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "module": {"type": "string", "enum": ["lead_factory"]},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 6,
            },
            "research": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 10,
            },
            "search_queries": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 6,
            },
            "output": {"type": "string"},
        },
        "required": ["module", "title", "summary", "actions", "research", "search_queries", "output"],
    },
}


def _clean_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _fallback_package(business_name: str, sector: str, location: str, goal: str, details: str) -> dict[str, Any]:
    research = [
        f"Cerca aziende e decision maker nel settore {sector} a {location}",
        f"Verifica quali servizi o bisogni compra il cliente ideale di {business_name}",
        "Individua i canali dove rispondono più velocemente: email, LinkedIn o WhatsApp",
    ]
    search_queries = [
        f"{sector} aziende {location}",
        f"migliori clienti per {sector}",
        f"contatti aziende {location} {sector}",
    ]
    actions = [
        "Definire il cliente ideale e il trigger d'acquisto",
        "Aprire 3 ricerche web per trovare target reali",
        "Scrivere email, LinkedIn e WhatsApp pronti all'invio",
        "Preparare follow-up e secondo contatto",
    ]
    output = (
        f"# AI Lead Factory\n\n"
        f"Obiettivo inserito: {goal}\n\n"
        f"Attivita: {business_name}\n"
        f"Settore: {sector}\n"
        f"Zona: {location}\n\n"
        f"## Ricerca da fare subito\n"
        f"- " + "\n- ".join(research) + "\n\n"
        f"## Query di ricerca\n"
        f"- " + "\n- ".join(search_queries) + "\n\n"
        f"## Pacchetto pronto\n"
        f"- 50 profili target da cercare nel mercato di riferimento\n"
        f"- Email iniziale personalizzata\n"
        f"- Messaggio LinkedIn breve\n"
        f"- Messaggio WhatsApp di apertura\n"
        f"- Follow-up dopo 3 giorni\n"
        f"- Follow-up finale dopo 7 giorni\n\n"
        f"## Angolo commerciale suggerito\n"
        f"{details or 'Parti da un messaggio semplice, diretto e orientato al risultato.'}\n\n"
        f"## Prossimo passo\n"
        f"Apri la ricerca, salva 10 target reali e invia il primo messaggio oggi."
    )
    return {
        "module": "lead_factory",
        "title": "Pacchetto commerciale pronto",
        "summary": f"Pacchetto pronto per {business_name} in {sector}. Strategia pensata per vendere piu velocemente a {location}.",
        "actions": actions,
        "research": research,
        "search_queries": search_queries,
        "output": output,
    }


def _call_openai_package(
    business_name: str,
    sector: str,
    location: str,
    goal: str,
    details: str,
) -> dict[str, Any] | None:
    client = get_openai_client()
    if client is None:
        return None

    prompt = (
        "You are AI Lead Factory. Create a real sales package for the user.\n"
        "Use web search to ground the package in realistic market research.\n"
        "Return practical targets, search queries, and outreach angles. Avoid generic advice.\n"
        "The response must be useful immediately for a business owner.\n\n"
        f"Business name: {business_name}\n"
        f"Sector: {sector}\n"
        f"Location: {location}\n"
        f"Goal: {goal}\n"
        f"Extra details: {details or 'none'}\n"
    )

    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "web_search"}],
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": PACKAGE_SCHEMA["name"],
                "schema": PACKAGE_SCHEMA["schema"],
                "strict": True,
            }
        },
    )

    output_text = getattr(response, "output_text", None)
    if not output_text:
        return None

    try:
        return _clean_json(output_text)
    except Exception:
        return None


def _merge_package_output(
    model_output: dict[str, Any] | None,
    fallback_output: dict[str, Any],
) -> dict[str, Any]:
    if model_output is None:
        return fallback_output

    merged = dict(fallback_output)
    merged.update(model_output)
    if not merged.get("research"):
        merged["research"] = list(fallback_output["research"])
    if not merged.get("search_queries"):
        merged["search_queries"] = list(fallback_output["search_queries"])
    if not merged.get("actions"):
        merged["actions"] = list(fallback_output["actions"])
    if not merged.get("output"):
        merged["output"] = fallback_output["output"]
    if not merged.get("summary"):
        merged["summary"] = fallback_output["summary"]
    if not merged.get("title"):
        merged["title"] = fallback_output["title"]
    merged["module"] = "lead_factory"
    return merged


class LeadFactoryService(BaseAssistantService):
    module_name = "lead_factory"

    def run(self, payload: AssistantRequest, db: Session | None = None) -> AssistantResponse:
        business = payload.business
        business_name = business.business_name.strip() or "la tua attivita"
        sector = business.sector.strip()
        location = business.location.strip()
        details = business.details.strip()
        goal = payload.goal.strip()
        fallback_output = _fallback_package(business_name, sector, location, goal, details)

        model_output = _call_openai_package(
            business_name=business_name,
            sector=sector,
            location=location,
            goal=goal,
            details=details,
        )

        model_output = _merge_package_output(model_output, fallback_output)

        result = AssistantResponse(
            module=model_output["module"],
            title=model_output["title"],
            summary=model_output["summary"],
            actions=list(model_output["actions"]),
            output=model_output["output"],
            research=list(model_output.get("research", [])),
            search_queries=list(model_output.get("search_queries", [])),
        )

        if db is not None:
            lead = save_lead(db, payload, result)
            result.lead_id = lead.id

        return result
