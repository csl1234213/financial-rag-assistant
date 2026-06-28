import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import io
from unittest.mock import patch

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


@pytest.mark.integration
class TestUploadAPI:
    def test_upload_valid_pdf(self, client):
        with patch("api.routers.upload.refresh_knowledge_base"):
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test_report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "upload success"
        assert data["file"] == "test_report.pdf"

    def test_upload_non_pdf_returns_400(self, client):
        response = client.post(
            "/api/v1/upload",
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_no_file_returns_422(self, client):
        response = client.post("/api/v1/upload")
        assert response.status_code == 422

    def test_upload_with_patch_preserves_filename(self, client):
        with patch("api.routers.upload.refresh_knowledge_base"):
            response = client.post(
                "/api/v1/upload",
                files={"file": ("financial_report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["file"] == "financial_report.pdf"
