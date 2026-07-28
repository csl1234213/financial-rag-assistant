import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from api.app import app
from models.document import Document
from models.tenant import Tenant
from storage.database import Base, get_db
from tests.storage_paths import create_sqlite_test_database

TEST_DATABASE_URL, engine = create_sqlite_test_database("test_knowledge_iso.db")
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


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


REGISTER_URL = "/api/v1/auth/register"
AUTH_ME_URL = "/api/v1/auth/me"
TENANT_ME_URL = "/api/v1/tenant/me"
KNOWLEDGE_URL = "/api/v1/knowledge"


def _register_and_get_token(client: TestClient, email: str = "test@example.com") -> str:
    resp = client.post(REGISTER_URL, json={"email": email, "password": "secure123"})
    assert resp.status_code == 201
    return resp.json()["token"]


class TestDocumentModel:
    def test_create_document_with_tenant(self, db_session):
        tenant = db_session.query(Tenant).filter(Tenant.slug == "default").first()
        doc = Document(
            filename="test_report.pdf",
            company="Tesla",
            report_type="Financial Report",
            period="Q2_2025",
            tenant_id=tenant.id,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.id is not None
        assert doc.filename == "test_report.pdf"
        assert doc.tenant_id == tenant.id
        assert doc.status == "indexed"

    def test_document_tenant_relationship(self, db_session):
        tenant = db_session.query(Tenant).filter(Tenant.slug == "default").first()
        doc = Document(
            filename="rel_doc.pdf",
            company="NVIDIA",
            period="Q3_2025",
            tenant_id=tenant.id,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.tenant is not None
        assert doc.tenant.id == tenant.id

        db_session.refresh(tenant)
        assert len(tenant.documents) >= 1


class TestTenantDocumentIsolation:
    def test_tenant_a_cannot_see_tenant_b_documents(self, db_session):
        tenant_a = db_session.query(Tenant).filter(Tenant.slug == "default").first()
        tenant_b = Tenant(name="Tenant B", slug="tenant-b")
        db_session.add(tenant_b)
        db_session.commit()
        db_session.refresh(tenant_b)

        doc_a = Document(
            filename="a_secret.pdf",
            company="Tesla",
            period="Q2_2025",
            tenant_id=tenant_a.id,
        )
        doc_b = Document(
            filename="b_secret.pdf",
            company="NVIDIA",
            period="Q3_2025",
            tenant_id=tenant_b.id,
        )
        db_session.add_all([doc_a, doc_b])
        db_session.commit()

        a_docs = (
            db_session.query(Document)
            .filter(Document.tenant_id == tenant_a.id)
            .all()
        )
        b_docs = (
            db_session.query(Document)
            .filter(Document.tenant_id == tenant_b.id)
            .all()
        )

        assert len(a_docs) == 1
        assert a_docs[0].filename == "a_secret.pdf"
        assert len(b_docs) == 1
        assert b_docs[0].filename == "b_secret.pdf"

    def test_knowledge_endpoint_requires_auth(self, client):
        response = client.get(KNOWLEDGE_URL)
        assert response.status_code == 401

    def test_knowledge_endpoint_tenant_scoped(self, client, db_session):
        token = _register_and_get_token(client, "knowledge-test@example.com")

        tenant = db_session.query(Tenant).filter(Tenant.slug == "default").first()
        doc = Document(
            filename="visible_doc.pdf",
            company="Tesla",
            period="Q2_2025",
            tenant_id=tenant.id,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get(
            KNOWLEDGE_URL, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "visible_doc.pdf" in data["documents"]

    def test_knowledge_statistics_tenant_scoped(self, client, db_session):
        token = _register_and_get_token(client, "stats-test@example.com")

        tenant = db_session.query(Tenant).filter(Tenant.slug == "default").first()
        doc = Document(
            filename="stats_doc.pdf",
            company="Apple",
            period="Q1_2025",
            tenant_id=tenant.id,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get(
            "/api/v1/knowledge/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] >= 1
