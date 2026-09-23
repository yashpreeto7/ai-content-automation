import pytest
from fastapi.testclient import TestClient
from src.server.app import app
from src.core.database import db

@pytest.fixture
def client():
    return TestClient(app)

def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "providers" in data
    assert "storage" in data

def test_list_projects(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
