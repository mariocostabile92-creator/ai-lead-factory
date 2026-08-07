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


def test_routes_goal_to_lead_factory(monkeypatch) -> None:
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


def test_recent_leads_are_not_public_without_login(monkeypatch) -> None:
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
