from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_routes_goal_to_lead_factory() -> None:
    response = client.post(
        "/api/assistant/run",
        json={
            "goal": "Voglio trovare nuovi clienti e preparare messaggi commerciali",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "Cerco clienti B2B",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "lead_factory"
    assert body["title"] == "Pacchetto commerciale pronto"
    assert body["lead_id"] is not None
    assert "50 profili target" in body["output"]


def test_recent_leads_contains_saved_item() -> None:
    response = client.post(
        "/api/assistant/run",
        json={
            "goal": "Voglio trovare nuovi clienti e preparare messaggi commerciali",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "Cerco clienti B2B",
            },
        },
    )
    lead_id = response.json()["lead_id"]

    recent = client.get("/api/leads/recent")
    assert recent.status_code == 200
    assert any(item["id"] == lead_id for item in recent.json())
