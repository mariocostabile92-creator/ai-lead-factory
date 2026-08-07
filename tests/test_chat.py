from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_creates_history() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Mi aiuti a trovare clienti nuovi?",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"]
    assert body["cta"]
    assert body["suggestions"]

    history = client.get(f"/api/chat/history/{body['conversation_id']}")
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["conversation_id"] == body["conversation_id"]
    assert len(history_body["messages"]) >= 2


def test_chat_returns_specific_outreach_draft() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Scrivimi una email di apertura",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_title"] == "Bozza email pronta"
    assert "Oggetto:" in body["draft"]
    assert "email" in body["cta"].lower()


def test_chat_returns_linkedin_draft_when_requested() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Scrivi un messaggio LinkedIn",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_title"] == "Messaggio LinkedIn pronto"
    assert "linkedin" in body["draft"].lower()


def test_chat_understands_real_target_search_request() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Cerca aziende target reali",
            "business": {
                "business_name": "Costabile SRL",
                "sector": "impianti elettrici",
                "location": "Como",
                "target": "amministratori di condominio e studi tecnici",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "leads"
    assert "amministratori di condominio" in body["reply"].lower()
    assert body["search_links"]
    assert "ordine nel lavoro" not in body["reply"].lower()


def test_chat_returns_follow_up_draft_when_requested() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Crea un follow-up",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "target": "studi professionali",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "outreach"
    assert body["draft_title"] == "Follow-up pronto"
    assert "studi professionali" in body["draft"].lower()
