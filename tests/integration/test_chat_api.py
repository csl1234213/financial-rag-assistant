import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from unittest.mock import MagicMock, patch

import pytest


def _make_fake_plan(intent="single_company", task_count=2):
    plan = MagicMock()
    plan.intent = intent
    plan.tasks = [MagicMock() for _ in range(task_count)]
    for i, t in enumerate(plan.tasks):
        t.step_id = i + 1
        t.step_type = MagicMock()
        t.step_type.value = "retrieve" if i == 0 else "synthesis"
        t.description = f"Task {i + 1}"
        t.company = "Apple"
        t.status = MagicMock()
        t.status.value = "completed"
    return plan


def _fake_run_rag_success(question, company=None):
    return (
        "# Investment Research Report\n\nRevenue grew 10%.",
        [
            {
                "rank": 1,
                "source": "apple.pdf",
                "chunk_id": "apple_0",
                "similarity": 0.95,
                "preview": "Revenue grew 10% year over year.",
            },
        ],
        "Evidence context...",
        "default",
        {"intent": "SINGLE_COMPANY", "companies": ["Apple"]},
        [],
        _make_fake_plan("single_company", 2),
        None,
        None,
    )


def _fake_run_rag_compare(question, company=None):
    return (
        "# Comparison Report\n\nApple vs Tesla analysis.",
        [
            {"rank": 1, "source": "apple.pdf", "chunk_id": "a_0", "similarity": 0.95, "preview": "Apple revenue."},
            {"rank": 2, "source": "tesla.pdf", "chunk_id": "t_0", "similarity": 0.90, "preview": "Tesla revenue."},
        ],
        "Compare context...",
        "compare",
        {"intent": "COMPARE_COMPANIES", "companies": ["Apple", "Tesla"]},
        [],
        _make_fake_plan("comparison", 4),
        None,
        None,
    )


def _fake_run_rag_empty(question, company=None):
    return (
        "No relevant evidence found in uploaded documents.",
        [],
        "",
        "default",
        {"intent": "GLOBAL_RESEARCH", "companies": None},
        [],
        _make_fake_plan("global_research", 2),
        None,
        None,
    )


@pytest.mark.integration
class TestChatAPI:
    def test_chat_normal_question(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_success,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "What is Apple's revenue?",
            })
        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        assert data["report"] != ""
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert len(data["citations"]) >= 1
        assert "reasoning" in data
        assert "intent" in data["reasoning"]
        assert "plan" in data
        assert "execution_time" in data

    def test_chat_compare_companies(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_compare,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "Compare Apple and Tesla revenue",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["report"] != ""
        assert len(data["citations"]) >= 2
        assert data["reasoning"]["intent"] == "COMPARE_COMPANIES"
        assert len(data["reasoning"]["companies"]) == 2

    def test_chat_unknown_company(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_empty,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "What is Microsoft's 1990 revenue?",
            })
        assert response.status_code == 200
        data = response.json()
        assert "No relevant evidence" in data["report"]
        assert data["citations"] == []

    def test_chat_empty_question_returns_422(self, client):
        response = client.post("/api/v1/chat", json={
            "question": "",
        })
        assert response.status_code == 422

    def test_chat_missing_question_returns_422(self, client):
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422

    def test_chat_with_company_filter(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_success,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "Revenue analysis",
                "company": "Apple",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["report"] != ""

    def test_chat_response_has_execution_time(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_success,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "Revenue analysis",
            })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["execution_time"], float)
        assert data["execution_time"] >= 0

    def test_chat_plan_structure(self, client):
        with patch(
            "api.services.chat_service.run_rag",
            side_effect=_fake_run_rag_success,
        ):
            response = client.post("/api/v1/chat", json={
                "question": "Revenue analysis",
            })
        assert response.status_code == 200
        data = response.json()
        assert "plan" in data
        assert "intent" in data["plan"]
        assert "task_count" in data["plan"]
        assert "tasks" in data["plan"]
        assert isinstance(data["plan"]["tasks"], list)