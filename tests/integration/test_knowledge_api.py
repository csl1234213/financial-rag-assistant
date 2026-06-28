import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest


@pytest.mark.integration
class TestKnowledgeAPI:
    def test_knowledge_status_code(self, client):
        response = client.get("/api/v1/knowledge")
        assert response.status_code == 200

    def test_knowledge_json_structure(self, client):
        response = client.get("/api/v1/knowledge")
        data = response.json()
        assert isinstance(data, dict)
        assert "documents" in data
        assert "document_count" in data
        assert "companies" in data

    def test_knowledge_documents_is_list(self, client):
        response = client.get("/api/v1/knowledge")
        data = response.json()
        assert isinstance(data["documents"], list)

    def test_knowledge_document_count_is_int(self, client):
        response = client.get("/api/v1/knowledge")
        data = response.json()
        assert isinstance(data["document_count"], int)

    def test_knowledge_companies_is_list(self, client):
        response = client.get("/api/v1/knowledge")
        data = response.json()
        assert isinstance(data["companies"], list)

    def test_knowledge_statistics_status_code(self, client):
        response = client.get("/api/v1/knowledge/statistics")
        assert response.status_code == 200

    def test_knowledge_statistics_json_structure(self, client):
        response = client.get("/api/v1/knowledge/statistics")
        data = response.json()
        assert isinstance(data, dict)
        assert "documents" in data
        assert "companies" in data
        assert "chunks" in data
        assert "embeddings" in data

    def test_knowledge_statistics_values_are_int(self, client):
        response = client.get("/api/v1/knowledge/statistics")
        data = response.json()
        assert isinstance(data["documents"], int)
        assert isinstance(data["companies"], int)
        assert isinstance(data["chunks"], int)
        assert isinstance(data["embeddings"], int)
