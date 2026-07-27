import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from unittest.mock import patch

import pytest


def _fake_agent_result(
    *,
    answer,
    citations,
    research_mode,
    intent,
    companies,
    strategy,
    workflow,
):
    return {
        "answer": answer,
        "citations": citations,
        "research_mode": research_mode,
        "evidence_count": len(citations),
        "intent": {"intent": intent, "companies": companies},
        "plan": {"intent": intent.lower(), "task_count": 2, "tasks": []},
        "routing": {"provider": "openai", "model": "gpt-4o"},
        "planning": {"task_type": "document_qa", "complexity": "low"},
        "execution": {"strategy": strategy},
        "workflow": {"type": workflow, "status": "DONE", "completed_steps": 3},
    }


def _fake_run_agent_success(question, company=None, **_request_scope):
    return _fake_agent_result(
        answer="# Investment Research Report\n\nRevenue grew 10%.",
        citations=[
            {
                "rank": 1,
                "source": "apple.pdf",
                "chunk_id": "apple_0",
                "similarity": 0.95,
                "preview": "Revenue grew 10% year over year.",
            },
        ],
        research_mode="default",
        intent="SINGLE_COMPANY",
        companies=["Apple"],
        strategy="rag",
        workflow="rag",
    )


def _fake_run_agent_compare(question, company=None, **_request_scope):
    return _fake_agent_result(
        answer="# Comparison Report\n\nApple vs Tesla analysis.",
        citations=[
            {"rank": 1, "source": "apple.pdf", "chunk_id": "a_0", "similarity": 0.95, "preview": "Apple revenue."},
            {"rank": 2, "source": "tesla.pdf", "chunk_id": "t_0", "similarity": 0.90, "preview": "Tesla revenue."},
        ],
        research_mode="compare",
        intent="COMPARE_COMPANIES",
        companies=["Apple", "Tesla"],
        strategy="parallel",
        workflow="parallel",
    )


def _fake_run_agent_empty(question, company=None, **_request_scope):
    return _fake_agent_result(
        answer="No relevant evidence found in uploaded documents.",
        citations=[],
        research_mode="default",
        intent="GLOBAL_RESEARCH",
        companies=[],
        strategy="multi_step",
        workflow="multi_step",
    )


@pytest.mark.integration
class TestChatAPI:
    def test_chat_normal_question(self, client):
        with patch(
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_success,
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
        assert data["citations"][0] == {
            "rank": 1,
            "source": "apple.pdf",
            "chunk_id": "apple_0",
            "similarity": 0.95,
            "preview": "Revenue grew 10% year over year.",
        }
        assert "reasoning" in data
        assert "intent" in data["reasoning"]
        assert "plan" in data
        assert "execution_time" in data
        assert data["routing"]["provider"] == "openai"
        assert data["execution"]["strategy"] == "rag"
        assert "provider" not in data["execution"]

    def test_chat_compare_companies(self, client):
        with patch(
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_compare,
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
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_empty,
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
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_success,
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
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_success,
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
            "api.services.chat_service.run_agent",
            side_effect=_fake_run_agent_success,
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
