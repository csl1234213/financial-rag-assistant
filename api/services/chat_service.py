import time
from typing import Optional

from api.schemas.response import ChatResponse
from core.core_engine import run_rag


class ChatService:
    """
    V4 Chat Service

    Single entry point for all clients (HTTP, CLI, Streamlit, etc.).

    Responsibilities:
    1. Accept ChatRequest
    2. Delegate to Agent Runtime via core_engine
    3. Map internal output to ChatResponse
    """

    def chat(
        self,
        question: str,
        company: Optional[str] = None,
    ) -> ChatResponse:
        t0 = time.time()

        report, citations, context, research_mode, intent_result, evidence, plan = run_rag(
            question,
            company=company,
        )

        reasoning = {
            "intent": intent_result.get("intent", ""),
            "companies": intent_result.get("companies", []),
            "research_mode": research_mode,
            "evidence_count": len(evidence),
        }

        plan_dict = {
            "intent": plan.intent,
            "task_count": len(plan.tasks),
            "tasks": [
                {
                    "step_id": t.step_id,
                    "step_type": t.step_type.value,
                    "description": t.description,
                    "company": t.company,
                    "status": t.status.value,
                }
                for t in plan.tasks
            ],
        }

        execution_time = round(time.time() - t0, 3)

        return ChatResponse(
            report=report,
            citations=citations,
            reasoning=reasoning,
            plan=plan_dict,
            execution_time=execution_time,
        )
