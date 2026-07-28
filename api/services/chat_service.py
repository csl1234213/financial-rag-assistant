import time
from typing import Optional

from api.schemas.response import ChatResponse
from services.agent_runtime.runtime import run_agent


class ChatService:
    """
    V5 Chat Service

    Single entry point for all clients (HTTP, CLI, Streamlit, etc.).

    Pipeline:
    Planning → Workflow → Execution → Routing → Provider
    """

    def chat(
        self,
        question: str,
        company: Optional[str] = None,
        *,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        thread_id: Optional[str] = None,
    ) -> ChatResponse:
        t0 = time.time()

        result = run_agent(
            question,
            company=company,
            tenant_id=tenant_id,
            user_id=user_id,
            thread_id=thread_id or "default",
        )
        intent_result = result.get("intent") or {}
        plan_dict = result.get("plan") or {}

        reasoning = {
            "intent": intent_result.get("intent", ""),
             "companies": intent_result.get("companies") or [],
            "research_mode": result.get("research_mode", "default"),
            "evidence_count": result.get("evidence_count", 0),
        }

        execution_time = round(time.time() - t0, 3)

        return ChatResponse(
            report=result.get("answer", ""),
            citations=result.get("citations", []),
            reasoning=reasoning,
            plan=plan_dict,
            execution_time=execution_time,
            routing=result.get("routing"),
            planning=result.get("planning"),
            execution=result.get("execution"),
            workflow=result.get("workflow"),
        )
