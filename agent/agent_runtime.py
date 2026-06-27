from typing import Optional

from agent.execution_plan import ExecutionPlan, StepType
from agent.execution_engine import ExecutionEngine
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from agent.reasoning_models import Evidence
from agent.runtime_context import RuntimeContext
from agent.runtime_result import RuntimeResult
from core.context_builder import build_context_from_evidence


class AgentRuntime:
    """
    V3.4 Agent Runtime

    Unified lifecycle manager for one AI Agent execution.

    Responsibilities:
    1. Intent analysis → Plan
    2. Execute via ExecutionEngine
    3. Collect evidence
    4. Build context & citations
    5. Reason via ReasoningEngine
    6. Return structured RuntimeResult

    Future entry points: Tool Registry, Memory, Reflection, Evaluation.
    """

    def __init__(
        self,
        planner: QueryPlanner,
        executor: ExecutionEngine,
        reasoner: ReasoningEngine,
        retriever,
        intent_analyzer,
    ):
        self.planner = planner
        self.executor = executor
        self.reasoner = reasoner
        self.retriever = retriever
        self.intent_analyzer = intent_analyzer

    # =========================
    # Main Entry
    # =========================

    def run(
        self,
        question: str,
        company: Optional[str] = None,
    ) -> RuntimeResult:
        """
        Execute the full Agent pipeline for one question.
        """

        # 1. Intent Analysis
        intent_result = self.intent_analyzer.analyze(question)

        if company is None and intent_result.get("companies"):
            company = intent_result["companies"][0]

        # 2. Plan
        plan = self.planner.plan(question, intent_result)

        # 3. Execute
        ctx = RuntimeContext(question=question, company=company)
        shared = {"_all_evidence": []}
        self.executor.execute(plan, shared)
        ctx.evidences = shared["_all_evidence"]

        # 4. Build Context & Citations
        context, citations = build_context_from_evidence(ctx.evidences)

        # 5. Reasoning
        execution_results = [
            step.result for step in plan.tasks
            if step.result is not None
        ]
        ctx.execution_results = execution_results
        reasoning_result = self.reasoner.analyze(execution_results)

        # 6. Result
        return RuntimeResult(
            reasoning_result=reasoning_result,
            context=context,
            citations=citations,
            evidence=ctx.evidences,
            plan=plan,
            intent_result=intent_result,
        )