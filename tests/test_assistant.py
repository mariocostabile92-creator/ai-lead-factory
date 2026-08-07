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
    assert "50 profili target" in body["output"]
