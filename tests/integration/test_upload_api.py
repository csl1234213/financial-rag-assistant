import io
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from api.app import app
from auth.dependencies import get_current_user
from models.document import Document
from models.task import Task
from models.tenant import Tenant
from models.user import User
from storage.database import Base, get_db
from tests.storage_paths import create_sqlite_test_database

TEST_DATABASE_URL, engine = create_sqlite_test_database("test_upload_api.db")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n190\n"
    b"%%EOF"
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    db_path = TEST_DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except (PermissionError, OSError):
            pass


@pytest.fixture
def user():
    db = TestingSessionLocal()
    try:
        tenant = Tenant(name="Upload Tenant", slug="upload-tenant")
        db.add(tenant)
        db.flush()
        current_user = User(
            email="upload@example.com",
            password_hash="not-used-in-this-test",
            tenant_id=tenant.id,
        )
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    finally:
        db.close()


@pytest.fixture
def client(user):
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def upload_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("api.routers.upload.UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("api.routers.upload.can_upload", lambda *_: True)
    monkeypatch.setattr("api.routers.upload.record_usage", lambda **_: None)
    broker = MagicMock()
    broker.enabled = False
    monkeypatch.setattr("api.routers.upload.get_broker", lambda: broker)
    return tmp_path


@pytest.mark.integration
class TestUploadAPI:
    def test_upload_requires_authentication(self):
        app.dependency_overrides[get_db] = _override_get_db
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/v1/upload",
                files={"file": ("test_report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )
        app.dependency_overrides.clear()
        assert response.status_code == 401

    def test_upload_valid_pdf_creates_tenant_document_and_task(self, client, upload_dir, user):
        response = client.post(
            "/api/v1/upload",
            files={"file": ("Tesla_Q2_2025.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "upload success"
        assert data["file"] == "Tesla_Q2_2025.pdf"
        assert data["status"] == "pending"

        db = TestingSessionLocal()
        try:
            document = db.get(Document, data["document_id"])
            task = db.query(Task).filter(Task.public_id == data["task_id"]).one()

            assert document is not None
            assert document.tenant_id == user.tenant_id
            assert document.status == "processing"
            assert task.tenant_id == user.tenant_id
            assert task.payload["document_id"] == document.id
            persisted_file = Path(task.payload["file_path"])
            assert persisted_file.is_relative_to(upload_dir)
            assert persisted_file.name == "Tesla_Q2_2025.pdf"
            assert persisted_file.read_bytes() == MINIMAL_PDF
        finally:
            db.close()

    def test_upload_non_pdf_returns_400(self, client, upload_dir):
        response = client.post(
            "/api/v1/upload",
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_rejects_non_pdf_content_with_pdf_extension(self, client, upload_dir):
        response = client.post(
            "/api/v1/upload",
            files={
                "file": (
                    "disguised.pdf",
                    io.BytesIO(b"this is not a PDF"),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Uploaded content is not a valid PDF document"

    def test_upload_enforces_size_limit(self, client, upload_dir, monkeypatch):
        monkeypatch.setattr("api.routers.upload.MAX_UPLOAD_BYTES", 10)
        response = client.post(
            "/api/v1/upload",
            files={"file": ("large.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
        )
        assert response.status_code == 413
