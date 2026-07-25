import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status(self):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_health_has_version(self):
        response = client.get("/health")
        data = response.json()
        assert "version" in data

    def test_health_has_database_status(self):
        response = client.get("/health")
        data = response.json()
        assert "database" in data
        assert data["database"] in ("ok", "unavailable", "disabled")

    def test_health_has_redis_status(self):
        response = client.get("/health")
        data = response.json()
        assert "redis" in data
        assert data["redis"] in ("ok", "disabled", "unavailable")

    def test_health_api_v1_path(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data