import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestRefreshAPI:
    def test_refresh_status_code(self, client):
        with patch("api.routers.refresh.refresh_knowledge_base"):
            response = client.post("/api/v1/refresh")
        assert response.status_code == 200

    def test_refresh_json_structure(self, client):
        with patch("api.routers.refresh.refresh_knowledge_base"):
            response = client.post("/api/v1/refresh")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "ok"
        assert "message" in data
        assert "knowledge base refreshed" in data["message"]
