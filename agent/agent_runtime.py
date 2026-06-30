from typing import Optional

from agent.execution_engine import ExecutionEngine
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from agent.runtime_context import RuntimeContext
from agent.runtime_result import RuntimeResult
from agent.planning import PlanningContext
from core.context_builder import build_context_from_evidence
from llm.router import ModelRouter


class AgentRuntime:
    """
    V4 Agent Runtime

    Unified lifecycle manager for one AI Agent execution.

    Responsibilities:
    1. Build PlanningContext → TaskAnalyzer → TaskResult
    2. QueryPlanner consumes TaskResult → ExecutionPlan
    3. Generate RoutingContext from TaskResult → Route to best Provider
    4. Execute via ExecutionEngine
    5. Collect evidence
    6. Build context & citations
    7. Reason via ReasoningEngine
    8. Return structured RuntimeResult with routing + planning info

    Future entry points: Tool Registry, Memory, Reflection, Evaluation.
    """

    def __init__(
        self,
        planner: QueryPlanner,
        executor: ExecutionEngine,
        reasoner: ReasoningEngine,
        retriever,
        intent_analyzer,
        router: Optional[ModelRouter] = None,
    ):
        self.planner = planner
        self.executor = executor
        self.reasoner = reasoner
        self.retriever = retriever
        self.intent_analyzer = intent_analyzer
        self.router = router

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

        # 1. Intent Analysis (legacy — for backward compat)
        intent_result = self.intent_analyzer.analyze(question)

        if company is None and intent_result.get("companies"):
            company = intent_result["companies"][0]

        # 2. Plan — TaskAnalyzer + ComplexityAnalyzer run inside QueryPlanner
        planning_context = PlanningContext(
            question=question,
            companies=intent_result.get("companies") or [],
        )
        plan, task_result, complexity_result = self.planner.plan(planning_context)

        # 3. Routing — from TaskResult + ComplexityResult
        routing_info = None
        if self.router is not None:
            routing_context = self.planner.build_routing_context(
                task_result,
                complexity_result,
            )
            routed = self.router.route(routing_context)
            routing_info = {
                "provider": routed["routing"].provider,
                "model": routed["routing"].model,
                "reason": routed["routing"].reason,
                "confidence": routed["routing"].confidence,
                "fallback_provider": routed["routing"].fallback_provider,
                "decision_time_ms": routed["routing"].decision_time_ms,
            }

        # 4. Planning info
        planning_info = {
            "task_type": task_result.task.task_type.value,
            "complexity": complexity_result.complexity.level.value,
            "complexity_score": complexity_result.complexity.score,
            "estimated_tokens": complexity_result.complexity.estimated_tokens,
            "estimated_latency_ms": complexity_result.complexity.estimated_latency_ms,
            "estimated_cost": complexity_result.complexity.estimated_cost,
            "reason": task_result.reason,
            "complexity_reason": complexity_result.reason,
            "planner_version": "rule-v1",
        }

        # 5. Execute
        ctx = RuntimeContext(question=question, company=company)
        shared = {"_all_evidence": []}
        self.executor.execute(plan, shared)
        ctx.evidences = shared["_all_evidence"]

        # 6. Build Context & Citations
        context, citations = build_context_from_evidence(ctx.evidences)

        # 7. Reasoning
        execution_results = [
            step.result for step in plan.tasks
            if step.result is not None
        ]
        ctx.execution_results = execution_results
        reasoning_result = self.reasoner.analyze(execution_results)

        # 8. Result
        return RuntimeResult(
            reasoning_result=reasoning_result,
            context=context,
            citations=citations,
            evidence=ctx.evidences,
            plan=plan,
            intent_result=intent_result,
            routing=routing_info,
            planning=planning_info,
        )