import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import app
from models.tenant import Tenant
from storage.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///./test_knowledge_integration.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        existing = db.query(Tenant).filter(Tenant.slug == "default").first()
        if existing is None:
            db.add(Tenant(name="Default Workspace", slug="default"))
            db.commit()
    finally:
        db.close()

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "knowledge-test@example.com",
        "password": "secure123",
    })
    assert resp.status_code == 201
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestKnowledgeAPI:
    def test_knowledge_status_code(self, client, auth_headers):
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        assert response.status_code == 200

    def test_knowledge_json_structure(self, client, auth_headers):
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        data = response.json()
        assert isinstance(data, dict)
        assert "documents" in data
        assert "document_count" in data
        assert "companies" in data

    def test_knowledge_documents_is_list(self, client, auth_headers):
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        data = response.json()
        assert isinstance(data["documents"], list)

    def test_knowledge_document_count_is_int(self, client, auth_headers):
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        data = response.json()
        assert isinstance(data["document_count"], int)

    def test_knowledge_companies_is_list(self, client, auth_headers):
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        data = response.json()
        assert isinstance(data["companies"], list)

    def test_knowledge_statistics_status_code(self, client, auth_headers):
        response = client.get("/api/v1/knowledge/statistics", headers=auth_headers)
        assert response.status_code == 200

    def test_knowledge_statistics_json_structure(self, client, auth_headers):
        response = client.get("/api/v1/knowledge/statistics", headers=auth_headers)
        data = response.json()
        assert isinstance(data, dict)
        assert "documents" in data
        assert "companies" in data
        assert "chunks" in data
        assert "embeddings" in data

    def test_knowledge_statistics_values_are_int(self, client, auth_headers):
        response = client.get("/api/v1/knowledge/statistics", headers=auth_headers)
        data = response.json()
        assert isinstance(data["documents"], int)
        assert isinstance(data["companies"], int)
        assert isinstance(data["chunks"], int)
        assert isinstance(data["embeddings"], int)