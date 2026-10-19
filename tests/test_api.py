
# FastAPI health endpoint test

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

def test_monitoring_status():

    response = client.get("/monitoring/status")

    assert response.status_code == 200

    data = response.json()

    assert "api" in data
    assert "database" in data
    assert "agent" in data
    assert "charts_generated" in data
    assert "reports_generated" in data

    # verificam valorile returnate de server
    assert data["api"] == "online"
    assert data["database"] in ["online", "offline"]
    assert data["agent"] in ["loaded", "unavailable"]

    # verificam daca numarul fisierelor este valid
    assert isinstance(data["charts_generated"], int)
    assert isinstance(data["reports_generated"], int)

    assert data["charts_generated"] >= 0
    assert data["reports_generated"] >= 0
