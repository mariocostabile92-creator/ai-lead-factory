from urllib.parse import urlparse


DEFAULT_STATUS = "Da contattare"


def _rating_value(rating: str) -> float | None:
    if not rating:
        return None
    first_token = rating.replace(",", ".").split(" ", maxsplit=1)[0]
    try:
        return float(first_token)
    except ValueError:
        return None


def score_prospect(item: dict[str, str], location: str) -> dict[str, str | int]:
    score = 5
    signals: list[str] = []

    if item.get("source") == "Google Places":
        score += 1
        signals.append("fonte Google Places")
    elif item.get("source") or item.get("url"):
        signals.append("fonte pubblica verificabile")

    if item.get("address"):
        score += 1
        if location and location.lower() in item["address"].lower():
            signals.append("indirizzo coerente con la zona richiesta")
        else:
            signals.append("indirizzo disponibile")

    if item.get("phone"):
        score += 1
        signals.append("telefono disponibile")

    if item.get("website"):
        score += 1
        signals.append("sito disponibile")
    elif item.get("maps_url"):
        signals.append("scheda Google Maps disponibile")

    rating_value = _rating_value(item.get("rating", ""))
    if rating_value is not None:
        score += 1 if rating_value >= 4 else 0
        signals.append(f"rating {item['rating']}")

    score = max(1, min(score, 10))
    if score >= 8:
        label = "Target forte"
    elif score >= 6:
        label = "Target medio"
    else:
        label = "Da valutare"

    reason = "Buon target perché " + ", ".join(signals) + "." if signals else (
        "Da valutare perché i dati disponibili sono limitati."
    )
    return {
        "target_score": score,
        "score_label": label,
        "score_reason": reason,
    }


def _safe_name(item: dict[str, str]) -> str:
    return item.get("title") or item.get("name") or "questa attività"


def build_sales_pack(
    item: dict[str, str],
    business_name: str,
    sector: str,
    location: str,
    target: str,
) -> dict[str, str | int]:
    target_focus = target or sector
    name = _safe_name(item)
    score = score_prospect(item, location)
    source = item.get("source") or urlparse(item.get("url", "")).netloc.replace("www.", "")
    category = item.get("category", "")
    contact_reason = (
        f"Vale la pena contattarlo perché è coerente con '{target_focus}' nella zona {location} "
        "e dispone di dati pubblici utili per un primo contatto."
    )

    email_subject = f"Proposta veloce per {name}"
    email_body = (
        f"Ciao {name},\n\n"
        f"ho visto la vostra attività a {location} e sto selezionando realtà vicine a {target_focus}.\n"
        f"{business_name} lavora nel settore {sector} e vorrei capire se può esserci un aggancio concreto.\n\n"
        "Se ha senso, ti mando due righe pratiche e valutiamo senza impegno.\n\n"
        "Grazie"
    )
    whatsapp_message = (
        f"Ciao {name}, sono {business_name}. Ho visto la vostra attività a {location} "
        f"e penso possa esserci un aggancio con {target_focus}. Ti posso mandare due righe?"
    )
    linkedin_message = (
        f"Ciao, ti scrivo perché sto selezionando realtà a {location} vicine a {target_focus}. "
        f"{business_name} lavora nel settore {sector}. Ti va se ti mando una proposta molto breve?"
    )
    follow_up_message = (
        f"Ciao {name}, ti riscrivo solo per capire se hai visto il messaggio precedente. "
        "Se non è il momento giusto nessun problema; in alternativa ti mando due righe concrete e valuti con calma."
    )

    return {
        "name": name,
        "category": category,
        "phone": item.get("phone", ""),
        "website": item.get("website", ""),
        "maps_url": item.get("maps_url", ""),
        "address": item.get("address", ""),
        "rating": item.get("rating", ""),
        "source": source,
        "fit_reason": str(score["score_reason"]),
        "message": email_body,
        "target_score": int(score["target_score"]),
        "score_label": str(score["score_label"]),
        "score_reason": str(score["score_reason"]),
        "contact_reason": contact_reason,
        "email_subject": email_subject,
        "email_body": email_body,
        "whatsapp_message": whatsapp_message,
        "linkedin_message": linkedin_message,
        "follow_up_message": follow_up_message,
        "status": DEFAULT_STATUS,
    }
