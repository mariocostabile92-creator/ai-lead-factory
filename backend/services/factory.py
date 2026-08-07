import json
import re
from html import unescape
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.schemas.common import AssistantRequest, AssistantResponse
from backend.services.base import BaseAssistantService
from backend.services.openai_client import call_with_timeout, get_openai_client
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
            "search_links": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 6,
            },
            "output": {"type": "string"},
        },
        "required": [
            "module",
            "title",
            "summary",
            "actions",
            "research",
            "search_queries",
            "search_links",
            "output",
        ],
    },
}


def _clean_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _build_search_links(search_queries: list[str]) -> list[str]:
    return [f"https://www.google.com/search?q={quote_plus(query)}" for query in search_queries]


def _fallback_package(business_name: str, sector: str, location: str, goal: str, target: str, details: str) -> dict[str, Any]:
    target_focus = target or sector
    research = [
        f"Cerca aziende e decision maker che corrispondono a: {target_focus} a {location}",
        f"Verifica quali servizi o bisogni compra il cliente ideale di {business_name}",
        "Individua i canali dove rispondono più velocemente: email, LinkedIn o WhatsApp",
    ]
    search_queries = [
        f"{target_focus} {sector} {location}",
        f"migliori clienti per {target_focus}",
        f"contatti aziende {location} {target_focus}",
    ]
    search_links = _build_search_links(search_queries)
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
        f"Target da cercare: {target or 'non specificato'}\n\n"
        f"## Ricerca da fare subito\n"
        f"- " + "\n- ".join(research) + "\n\n"
        f"## Query di ricerca\n"
        f"- " + "\n- ".join(search_queries) + "\n\n"
        f"## Link da aprire subito\n"
        f"- " + "\n- ".join(search_links) + "\n\n"
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
        "search_links": search_links,
        "output": output,
    }


def _clean_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", unescape(cleaned)).strip()


def _normalize_search_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target_url = parse_qs(parsed.query).get("uddg", [""])[0]
        if target_url:
            return unquote(target_url)
    return url


def _extract_search_results(html: str, limit: int = 6) -> list[dict[str, str]]:
    pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        url = _normalize_search_url(unescape(match.group("url")))
        title = _clean_html(match.group("title"))
        if not url.startswith("http") or not title or url in seen:
            continue
        seen.add(url)
        results.append({"title": title, "url": url})
        if len(results) >= limit:
            break
    return results


def _package_search_queries(sector: str, location: str, target: str) -> list[str]:
    target_focus = target or sector
    return [
        f"{target_focus} {location}",
        f"aziende {sector} {location}",
        f"contatti decision maker {target_focus} {location}",
        f"site:linkedin.com/company {target_focus} {location}",
        f"Google Maps {target_focus} {location}",
    ]


def _search_web(search_queries: list[str], limit: int = 8) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    headers = {"User-Agent": "Mozilla/5.0 AI Lead Factory research assistant"}
    try:
        with httpx.Client(timeout=4.0, follow_redirects=True, headers=headers) as client:
            for query in search_queries[:3]:
                response = client.get("https://html.duckduckgo.com/html/", params={"q": query})
                response.raise_for_status()
                for item in _extract_search_results(response.text, limit=5):
                    if item["url"] in seen:
                        continue
                    seen.add(item["url"])
                    results.append(item)
                    if len(results) >= limit:
                        return results
    except Exception:
        return results
    return results


def _format_prospect_rows(search_results: list[dict[str, str]]) -> str:
    if not search_results:
        return (
            "## Prospect da verificare\n"
            "- Nessun risultato automatico disponibile in questo momento. Usa i link di ricerca sotto per aprire fonti reali e salvare i primi prospect.\n"
        )

    rows = ["## Prospect trovati da verificare"]
    for index, item in enumerate(search_results[:8], start=1):
        domain = urlparse(item["url"]).netloc.replace("www.", "")
        rows.append(f"{index}. {item['title']} - fonte: {domain} - {item['url']}")
    return "\n".join(rows) + "\n"


def _operational_package(
    business_name: str,
    sector: str,
    location: str,
    goal: str,
    target: str,
    details: str,
    search_results: list[dict[str, str]],
) -> dict[str, Any]:
    target_focus = target or sector
    search_queries = _package_search_queries(sector, location, target)
    search_links = [item["url"] for item in search_results[:6]] or _build_search_links(search_queries)
    research = [
        f"Target operativo: {target_focus}",
        f"Zona prioritaria: {location}",
        "Fonti da usare: Google Maps, LinkedIn, registri imprese, associazioni locali",
        "Criteri di qualifica: settore coerente, dimensione azienda, referente raggiungibile, segnale di bisogno",
    ]
    research.extend([f"{item['title']} - {item['url']}" for item in search_results[:5]])
    actions = [
        "Aprire i prospect trovati e scartare quelli non coerenti",
        "Salvare nome azienda, sito, referente e canale migliore",
        "Inviare email o LinkedIn adattati al target",
        "Preparare follow-up a 3 e 7 giorni",
    ]
    output = (
        f"# AI Lead Factory\n\n"
        f"Obiettivo inserito: {goal}\n\n"
        f"Attivita: {business_name}\n"
        f"Settore: {sector}\n"
        f"Zona: {location}\n"
        f"Target da cercare: {target_focus}\n\n"
        f"{_format_prospect_rows(search_results)}\n"
        f"## Query pronte\n"
        f"- " + "\n- ".join(search_queries) + "\n\n"
        f"## Link/prospect da aprire subito\n"
        f"- " + "\n- ".join(search_links) + "\n\n"
        f"## Sequenza pronta\n"
        f"- Lista prospect iniziale da verificare e completare\n"
        f"- Email iniziale personalizzata sul target: {target_focus}\n"
        f"- Messaggio LinkedIn breve per referente o pagina aziendale\n"
        f"- Messaggio WhatsApp solo se il numero e pubblico o gia autorizzato\n"
        f"- Follow-up dopo 3 giorni\n"
        f"- Follow-up finale dopo 7 giorni\n\n"
        f"## Email iniziale\n"
        f"Oggetto: proposta veloce per {location}\n\n"
        f"Ciao, ho visto la vostra attivita e credo possa esserci un aggancio con {business_name}.\n"
        f"Lavoriamo nel settore {sector} e stiamo cercando realta come la vostra tra {target_focus}.\n"
        f"Se ha senso, ti mando due righe concrete per capire se possiamo aiutarti.\n\n"
        f"## Messaggio LinkedIn\n"
        f"Ciao, ti scrivo perche sto selezionando realta a {location} vicine a {target_focus}. "
        f"{business_name} lavora nel settore {sector}. Ti va se ti mando una proposta molto breve?\n\n"
        f"## Angolo commerciale suggerito\n"
        f"{details or 'Parti da un messaggio semplice, diretto e orientato al risultato.'}\n\n"
        f"## Prossimo passo\n"
        f"Apri i prospect/link, salva 10 aziende vere con referente e poi usa la chat per personalizzare ogni messaggio."
    )
    return {
        "module": "lead_factory",
        "title": "Ricerca commerciale pronta",
        "summary": f"Ricerca e sequenza per vendere a {target_focus} in zona {location}.",
        "actions": actions,
        "research": research[:10],
        "search_queries": search_queries,
        "search_links": search_links,
        "output": output,
    }


def _call_openai_package(
    business_name: str,
    sector: str,
    location: str,
    goal: str,
    target: str,
    details: str,
    search_results: list[dict[str, str]],
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
        f"Target to research: {target or 'none'}\n"
        f"Extra details: {details or 'none'}\n"
        f"Search results already collected: {json.dumps(search_results[:8], ensure_ascii=False)}\n"
    )

    response = call_with_timeout(
        lambda: client.responses.create(
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
        ),
        timeout_seconds=12.0,
    )

    if response is None:
        return None

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
    if not merged.get("search_links"):
        merged["search_links"] = list(fallback_output["search_links"])
    else:
        merged["search_links"] = list(dict.fromkeys(list(fallback_output["search_links"]) + list(merged["search_links"])))[:6]
    if not merged.get("actions"):
        merged["actions"] = list(fallback_output["actions"])
    if not merged.get("output"):
        merged["output"] = fallback_output["output"]
    elif "Prospect trovati da verificare" in fallback_output["output"] and "Prospect trovati da verificare" not in merged["output"]:
        merged["output"] = f"{fallback_output['output']}\n\n## Analisi AI aggiuntiva\n{merged['output']}"
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
        target = business.target.strip()
        details = business.details.strip()
        goal = payload.goal.strip()
        search_results = _search_web(_package_search_queries(sector, location, target))
        fallback_output = _operational_package(business_name, sector, location, goal, target, details, search_results)

        model_output = _call_openai_package(
            business_name=business_name,
            sector=sector,
            location=location,
            goal=goal,
            target=target,
            details=details,
            search_results=search_results,
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
            search_links=list(model_output.get("search_links", [])),
        )

        if db is not None and settings.enable_public_storage:
            lead = save_lead(db, payload, result)
            result.lead_id = lead.id

        return result
