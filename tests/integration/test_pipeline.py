import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import io
from unittest.mock import MagicMock, patch

import pytest

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


def _make_fake_plan():
    plan = MagicMock()
    plan.intent = "single_company"
    plan.tasks = []
    return plan


def _fake_run_rag(question, company=None):
    return (
        "# Pipeline Test Report\n\nAll systems operational.",
        [
            {"rank": 1, "source": "pipeline_test.pdf", "chunk_id": "pt_0", "similarity": 0.99, "preview": "OK"},
        ],
        "Pipeline context...",
        "default",
        {"intent": "SINGLE_COMPANY", "companies": ["TestCorp"]},
        [],
        _make_fake_plan(),
        None,
        None,
    )


@pytest.mark.integration
class TestPipeline:
    def test_full_pipeline_upload_refresh_chat(self, client):
        with patch("api.routers.refresh.refresh_knowledge_base"):
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": ("pipeline_test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )
        assert upload_response.status_code == 200
        assert upload_response.json()["message"] == "upload success"

        with patch("api.routers.refresh.refresh_knowledge_base"):
            refresh_response = client.post("/api/v1/refresh")
        assert refresh_response.status_code == 200
        assert refresh_response.json()["status"] == "ok"

        with patch("api.services.chat_service.run_rag", side_effect=_fake_run_rag):
            chat_response = client.post("/api/v1/chat", json={
                "question": "Is the system operational?",
            })
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert chat_data["report"] != ""
        assert len(chat_data["citations"]) >= 1
        assert chat_data["citations"][0]["source"] == "pipeline_test.pdf"

    def test_pipeline_knowledge_after_upload(self, client):
        with patch("api.routers.refresh.refresh_knowledge_base"):
            client.post(
                "/api/v1/upload",
                files={"file": ("knowledge_test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )

        knowledge_response = client.get("/api/v1/knowledge")
        assert knowledge_response.status_code == 200
        data = knowledge_response.json()
        assert isinstance(data["documents"], list)
        assert isinstance(data["document_count"], int)
        assert isinstance(data["companies"], list)

    def test_pipeline_health_after_operations(self, client):
        with patch("api.routers.refresh.refresh_knowledge_base"):
            client.post(
                "/api/v1/upload",
                files={"file": ("health_test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )

        health_response = client.get("/api/v1/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"