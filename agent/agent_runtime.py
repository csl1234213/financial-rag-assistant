import logging
from typing import Optional

from agent.execution_engine import ExecutionEngine
from agent.execution.execution_context import ExecutionContext
from agent.execution.execution_engine import ExecutionEngine as StrategyExecutionEngine
from agent.execution.execution_dispatcher import ExecutionDispatcher
from agent.execution.execution_handler import ExecutionHandlerContext
from agent.execution.handlers import (  # noqa: F401 — auto-registration
    RagHandler,
    DirectLLMHandler,
    ParallelHandler,
    MultiStepHandler,
    ToolCallingHandler,
)
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from agent.runtime_context import RuntimeContext
from agent.runtime_result import RuntimeResult
from agent.runtime_state import RuntimeState
from agent.planning import PlanningContext
from agent.workflow.workflow_bridge import WorkflowBridge
from agent.workflow.workflow_context import WorkflowContext
from agent.workflow.workflow_engine import WorkflowEngine
from agent.workflow.workflow_executor import WorkflowExecutor
from core.context_builder import build_context_from_evidence
from llm.router import ModelRouter

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    V5 Agent Runtime

    Unified lifecycle manager for one AI Agent execution.

    Pipeline:
    1. Planning — TaskAnalyzer + ComplexityAnalyzer
    2. Execution Strategy — determine HOW to execute
    3. Workflow — WorkflowEngine + WorkflowExecutor
    4. Execution Dispatch — actual execution via handlers
    5. Reasoning — ReasoningEngine

    Workflow is now the default entry point for execution.
    Even a single-step DirectChatWorkflow goes through the same pipeline.
    """

    def __init__(
        self,
        planner: QueryPlanner,
        executor: ExecutionEngine,
        reasoner: ReasoningEngine,
        retriever,
        intent_analyzer,
        router: Optional[ModelRouter] = None,
        strategy_engine: Optional[StrategyExecutionEngine] = None,
        dispatcher: Optional[ExecutionDispatcher] = None,
        workflow_engine: Optional[WorkflowEngine] = None,
        workflow_executor: Optional[WorkflowExecutor] = None,
    ):
        self.planner = planner
        self.executor = executor
        self.reasoner = reasoner
        self.retriever = retriever
        self.intent_analyzer = intent_analyzer
        self.router = router
        self.strategy_engine = strategy_engine
        self.dispatcher = dispatcher
        self.workflow_engine = workflow_engine or WorkflowEngine()
        self.workflow_executor = workflow_executor or WorkflowExecutor()

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
        routing_context = None
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

        if routing_context is None:
            from llm.router import RoutingContext as RC
            routing_context = RC(task=task_result.task.task_type)

        # 4. Execution Strategy — determine HOW to execute
        strategy_result = None
        if self.strategy_engine is not None:
            exec_ctx = ExecutionContext(
                task=task_result,
                complexity=complexity_result,
                routing=routing_context,
            )
            strategy_result = self.strategy_engine.execute(exec_ctx)
            logger.info(
                "Execution Strategy: %s | Reason: %s | Steps: %d | Parallelism: %d | Confidence: %.2f",
                strategy_result.strategy.value,
                strategy_result.reason,
                strategy_result.estimated_steps,
                strategy_result.parallelism,
                strategy_result.confidence,
            )

        strategy_info = None
        if strategy_result is not None:
            strategy_info = {
                "strategy": strategy_result.strategy.value,
                "reason": strategy_result.reason,
                "estimated_steps": strategy_result.estimated_steps,
                "parallelism": strategy_result.parallelism,
                "use_retrieval": strategy_result.use_retrieval,
                "use_tools": strategy_result.use_tools,
                "confidence": strategy_result.confidence,
            }

        # 5. Planning info
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

        # ============================================================
        # 6. Workflow — WorkflowEngine → WorkflowExecutor → WorkflowResult
        # ============================================================
        workflow_info = None
        workflow_result = None
        runtime_state = RuntimeState()

        if strategy_result is not None and self.strategy_engine is not None:
            workflow_ctx = WorkflowContext(
                task=task_result,
                complexity=complexity_result,
                execution=strategy_result,
                routing=routing_context,
            )

            workflow_result = self.workflow_engine.build(workflow_ctx)

            bridge_ctx = WorkflowBridge.to_execution_context(
                workflow_ctx,
                workflow_result,
            )

            workflow_result = self.workflow_executor.execute(
                workflow_result,
                self.strategy_engine,
                bridge_ctx,
            )

            runtime_state.workflow = workflow_result

            workflow_info = {
                "type": workflow_result.workflow.value,
                "status": workflow_result.status.value,
                "completed_steps": len(workflow_result.completed_steps),
                "total_steps": len(workflow_result.steps),
                "estimated_time_ms": workflow_result.estimated_time_ms,
                "confidence": workflow_result.confidence,
                "reason": workflow_result.reason,
            }

            logger.info(
                "Workflow: %s | Status: %s | Steps: %d/%d",
                workflow_result.workflow.value,
                workflow_result.status.value,
                len(workflow_result.completed_steps),
                len(workflow_result.steps),
            )

        # 7. Execute — dispatch via ExecutionDispatcher (unchanged)
        ctx = RuntimeContext(question=question, company=company)

        if self.dispatcher is not None and strategy_result is not None:
            handler_ctx = ExecutionHandlerContext(
                plan=plan,
                executor=self.executor,
            )
            output = self.dispatcher.dispatch(strategy_result, handler_ctx)
            ctx.evidences = output.evidences
            context = output.context
            citations = output.citations
            execution_results = output.execution_results
        else:
            shared = {"_all_evidence": []}
            self.executor.execute(plan, shared)
            ctx.evidences = shared["_all_evidence"]
            context, citations = build_context_from_evidence(ctx.evidences)
            execution_results = [
                step.result for step in plan.tasks
                if step.result is not None
            ]

        # 8. Reasoning
        ctx.execution_results = execution_results
        reasoning_result = self.reasoner.analyze(execution_results)

        # 9. Result
        return RuntimeResult(
            reasoning_result=reasoning_result,
            context=context,
            citations=citations,
            evidence=ctx.evidences,
            plan=plan,
            intent_result=intent_result,
            routing=routing_info,
            planning=planning_info,
            execution=strategy_info,
            workflow=workflow_info,
        )