from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def fake_search_results(*_args, **_kwargs) -> list[dict[str, str]]:
    return [
        {
            "title": "Studio Tecnico Demo Como",
            "url": "https://example.com/studio-tecnico-demo",
        }
    ]


def fake_places_results(*_args, **_kwargs) -> list[dict[str, str]]:
    return [
        {
            "title": "Studio Tecnico Places Como",
            "url": "https://maps.google.com/?cid=123",
            "source": "Google Places",
            "address": "Via Roma 1, Como",
            "phone": "031 123456",
            "website": "",
            "maps_url": "https://maps.google.com/?cid=123",
            "rating": "4.7 (18 recensioni)",
        }
    ]


def test_routes_goal_to_lead_factory(monkeypatch) -> None:
    monkeypatch.setattr("backend.services.factory._search_google_places", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("backend.services.factory._search_web", fake_search_results)
    response = client.post(
        "/api/assistant/run",
        json={
            "goal": "Voglio trovare nuovi clienti e preparare messaggi commerciali",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "target": "studi tecnici",
                "details": "Cerco clienti B2B",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "lead_factory"
    assert body["title"] == "Ricerca commerciale pronta"
    assert body["lead_id"] is None
    assert "Prospect trovati da verificare" in body["output"]
    assert "Studio Tecnico Demo Como" in body["output"]
    assert body["search_links"] == ["https://example.com/studio-tecnico-demo"]
    assert body["prospects"][0]["name"] == "Studio Tecnico Demo Como"
    assert body["prospects"][0]["fit_reason"]
    assert "Demo SRL" in body["prospects"][0]["message"]


def test_recent_leads_are_not_public_without_login(monkeypatch) -> None:
    monkeypatch.setattr("backend.services.factory._search_google_places", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("backend.services.factory._search_web", fake_search_results)
    client.post(
        "/api/assistant/run",
        json={
            "goal": "Voglio trovare nuovi clienti e preparare messaggi commerciali",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "target": "studi tecnici",
                "details": "Cerco clienti B2B",
            },
        },
    )

    recent = client.get("/api/leads/recent")
    assert recent.status_code == 200
    assert recent.json() == []


def test_routes_goal_uses_google_places_prospects(monkeypatch) -> None:
    monkeypatch.setattr("backend.services.factory._search_google_places", fake_places_results)
    monkeypatch.setattr("backend.services.factory._search_web", lambda *_args, **_kwargs: [])
    response = client.post(
        "/api/assistant/run",
        json={
            "goal": "Voglio trovare nuovi clienti",
            "business": {
                "business_name": "Demo SRL",
                "sector": "impianti elettrici",
                "location": "Como",
                "target": "studi tecnici",
                "details": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "Studio Tecnico Places Como" in body["output"]
    assert "Via Roma 1, Como" in body["output"]
    assert "031 123456" in body["output"]
    assert body["search_links"] == ["https://maps.google.com/?cid=123"]
    assert body["prospects"][0]["phone"] == "031 123456"
    assert body["prospects"][0]["rating"] == "4.7 (18 recensioni)"
    assert "Studio Tecnico Places Como" in body["prospects"][0]["message"]
