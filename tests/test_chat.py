from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_routes_to_leads() -> None:
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
    assert body["module"] == "leads"
    assert body["suggestions"]


def test_chat_routes_to_operations() -> None:
    response = client.post(
        "/api/chat/respond",
        json={
            "message": "Organizza le mie priorità di oggi",
            "business": {
                "business_name": "Demo SRL",
                "sector": "servizi",
                "location": "Milano",
                "details": "",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["module"] == "operations"
