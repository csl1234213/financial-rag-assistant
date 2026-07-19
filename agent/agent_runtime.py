import logging
import time
from typing import Optional

from agent.execution.execution_context import ExecutionContext
from agent.execution.execution_dispatcher import ExecutionDispatcher
from agent.execution.execution_engine import ExecutionEngine as StrategyExecutionEngine
from agent.execution.execution_handler import ExecutionHandlerContext
from agent.execution.handlers import (  # noqa: F401 — auto-registration
    DirectLLMHandler,
    MultiStepHandler,
    ParallelHandler,
    RagHandler,
    ToolCallingHandler,
)
from agent.execution_engine import ExecutionEngine
from agent.memory.memory_bridge import MemoryBridge
from agent.memory.memory_engine import MemoryEngine
from agent.metrics.metric_bridge import MetricBridge
from agent.metrics.metric_engine import MetricEngine
from agent.metrics.metric_enums import MetricScope, MetricType
from agent.planning import PlanningContext
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from agent.reliability.reliability_bridge import ReliabilityBridge
from agent.reliability.reliability_engine import ReliabilityEngine
from agent.runtime_context import RuntimeContext
from agent.runtime_result import RuntimeResult
from agent.runtime_state import RuntimeState
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
    1. Intent Analysis
    2. Memory Retrieve — retrieve historical context
    3. Planning — TaskAnalyzer + ComplexityAnalyzer
    4. Routing — ModelRouter
    5. Execution Strategy — determine HOW to execute
    6. Workflow — WorkflowEngine + WorkflowExecutor
    7. Execution Dispatch — actual execution via handlers
    8. Reasoning — ReasoningEngine
    9. Memory Store — persist execution result

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
        memory_engine: Optional[MemoryEngine] = None,
        metric_engine: Optional[MetricEngine] = None,
        reliability_engine: Optional[ReliabilityEngine] = None,
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
        self.memory_engine = memory_engine
        self.metric_engine = metric_engine
        self.reliability_engine = reliability_engine

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

        runtime_start = time.time()

        # 1. Intent Analysis (legacy — for backward compat)
        intent_result = self.intent_analyzer.analyze(question)

        if company is None and intent_result.get("companies"):
            company = intent_result["companies"][0]

        # 2. Memory Retrieve — retrieve historical context
        memory_retrieve_info = None
        if self.memory_engine is not None:
            retrieve_ctx = MemoryBridge.to_memory_context(
                task_result=None,
                runtime_state=RuntimeState(),
                question=question,
                company=company,
            )
            retrieve_result = self.memory_engine.retrieve(retrieve_ctx)
            memory_retrieve_info = {
                "retrieved_count": retrieve_result.retrieved_count,
                "confidence": retrieve_result.confidence,
                "reason": retrieve_result.reason,
            }
            logger.info(
                "Memory Retrieve: %d records | Confidence: %.2f",
                retrieve_result.retrieved_count,
                retrieve_result.confidence,
            )

        # 3. Plan — TaskAnalyzer + ComplexityAnalyzer run inside QueryPlanner
        planning_context = PlanningContext(
            question=question,
            companies=intent_result.get("companies") or [],
        )
        plan, task_result, complexity_result = self.planner.plan(planning_context)

        # 4. Routing — from TaskResult + ComplexityResult
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

        # 5. Execution Strategy — determine HOW to execute
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

        # 6. Planning info
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
        # 7. Workflow — WorkflowEngine → WorkflowExecutor → WorkflowResult
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

        # 8. Execute — dispatch via ExecutionDispatcher
        ctx = RuntimeContext(question=question, company=company)
        reliability_info = None

        if self.dispatcher is not None and strategy_result is not None:
            handler_ctx = ExecutionHandlerContext(
                plan=plan,
                executor=self.executor,
            )

            _execution_output: list = []

            def _execution_callable():
                output = self.dispatcher.dispatch(strategy_result, handler_ctx)
                _execution_output.append(output)

            if self.reliability_engine is not None:
                reliability_ctx = ReliabilityBridge.to_reliability_context(
                    runtime_state,
                    metadata={
                        "_callable": _execution_callable,
                        "phase": "execution",
                    },
                )

                pipeline_result = self.reliability_engine.execute_pipeline(
                    reliability_ctx,
                )

                runtime_state.retry_count = 0
                runtime_state.timeout_count = 0
                runtime_state.fallback_used = False
                for mechanism_name, result in pipeline_result.results.items():
                    if mechanism_name == "retry":
                        runtime_state.retry_count = result.retry_count
                    elif mechanism_name == "timeout":
                        if result.timeout_occurred:
                            runtime_state.timeout_count += 1
                    elif mechanism_name == "circuit_breaker":
                        runtime_state.circuit_state = result.circuit_state
                        runtime_state.failure_count = result.metadata.get("failure_count", 0)
                    elif mechanism_name == "health_check":
                        runtime_state.health_status = result.metadata.get("health_status")
                    elif mechanism_name == "rate_limiter":
                        runtime_state.rate_limit_remaining = result.metadata.get("rate_limit_remaining", 0)
                    elif mechanism_name == "fallback":
                        runtime_state.fallback_used = result.metadata.get("fallback_used", False)

                reliability_info = {
                    "pipeline": pipeline_result.pipeline_order,
                    "total_latency_ms": pipeline_result.total_latency_ms,
                    "retry_count": runtime_state.retry_count,
                    "timeout_count": runtime_state.timeout_count,
                    "circuit_state": runtime_state.circuit_state,
                    "failure_count": runtime_state.failure_count,
                    "health_status": runtime_state.health_status,
                    "rate_limit_remaining": runtime_state.rate_limit_remaining,
                    "fallback_used": runtime_state.fallback_used,
                }

                if not pipeline_result.success:
                    raise RuntimeError(f"Execution failed after reliability pipeline: {pipeline_result.pipeline_order}")

                if self.metric_engine is not None:
                    metric_ctx = MetricBridge.to_metric_context(
                        state=runtime_state,
                        metadata={"phase": "reliability"},
                    )
                    self.metric_engine.increment(
                        metric_ctx,
                        "retry_total",
                        value=float(runtime_state.retry_count),
                        scope=MetricScope.RUNTIME,
                    )
                    if runtime_state.retry_count == 0:
                        self.metric_engine.increment(
                            metric_ctx,
                            "retry_success",
                            value=1.0,
                            scope=MetricScope.RUNTIME,
                        )
                    if runtime_state.timeout_count > 0:
                        self.metric_engine.increment(
                            metric_ctx,
                            "timeout_total",
                            value=float(runtime_state.timeout_count),
                            scope=MetricScope.RUNTIME,
                        )
                    if runtime_state.circuit_state:
                        self.metric_engine.increment(
                            metric_ctx,
                            f"circuit_{runtime_state.circuit_state}_total",
                            value=1.0,
                            scope=MetricScope.RUNTIME,
                        )
                    if runtime_state.health_status == "unhealthy":
                        self.metric_engine.increment(
                            metric_ctx,
                            "health_check_failed",
                            value=1.0,
                            scope=MetricScope.RUNTIME,
                        )
                    self.metric_engine.increment(
                        metric_ctx,
                        "health_check_total",
                        value=1.0,
                        scope=MetricScope.RUNTIME,
                    )
                    self.metric_engine.increment(
                        metric_ctx,
                        "rate_limit_total",
                        value=1.0,
                        scope=MetricScope.RUNTIME,
                    )
                    if runtime_state.rate_limit_remaining == 0:
                        self.metric_engine.increment(
                            metric_ctx,
                            "rate_limit_blocked",
                            value=1.0,
                            scope=MetricScope.RUNTIME,
                        )
                    if runtime_state.fallback_used:
                        self.metric_engine.increment(
                            metric_ctx,
                            "fallback_total",
                            value=1.0,
                            scope=MetricScope.RUNTIME,
                        )
            else:
                _execution_callable()

            output = _execution_output[0]
            ctx.evidences = output.evidences
            context = output.context
            citations = output.citations
            execution_results = output.execution_results
        else:
            shared = {"_all_evidence": []}
            self.executor.execute(plan, shared)
            ctx.evidences = shared["_all_evidence"]
            context, citations = build_context_from_evidence(ctx.evidences)
            execution_results = [step.result for step in plan.tasks if step.result is not None]

        # 9. Reasoning
        ctx.execution_results = execution_results
        reasoning_result = self.reasoner.analyze(execution_results)

        # 10. Memory Store — persist execution result
        memory_store_info = None
        if self.memory_engine is not None:
            memory_ctx = MemoryBridge.to_memory_context(
                task_result=task_result,
                runtime_state=runtime_state,
                question=question,
                company=company,
            )
            store_result = self.memory_engine.store(memory_ctx)
            memory_store_info = {
                "stored_count": store_result.retrieved_count,
                "confidence": store_result.confidence,
                "reason": store_result.reason,
            }
            logger.info(
                "Memory Store: %d records | Confidence: %.2f",
                store_result.retrieved_count,
                store_result.confidence,
            )

        # 11. Metrics — collect runtime metrics
        metrics_result = None
        if self.metric_engine is not None:
            metric_ctx = MetricBridge.to_metric_context(
                state=runtime_state,
                metadata={
                    "runtime_id": str(id(self)),
                    "question": question,
                    "company": company or "",
                },
            )

            runtime_duration_ms = (time.time() - runtime_start) * 1000
            self.metric_engine.observe(
                metric_ctx,
                "runtime_duration",
                runtime_duration_ms,
                metric_type=MetricType.TIMER,
                scope=MetricScope.RUNTIME,
            )

            if workflow_info is not None:
                workflow_duration = workflow_info.get("estimated_time_ms", 0)
                labels = MetricBridge.extract_labels(runtime_state)
                self.metric_engine.observe(
                    metric_ctx,
                    "workflow_duration",
                    float(workflow_duration),
                    metric_type=MetricType.TIMER,
                    scope=MetricScope.WORKFLOW,
                    labels=labels,
                )

            if workflow_info is not None:
                completed_steps = workflow_info.get("completed_steps", 0)
                self.metric_engine.increment(
                    metric_ctx,
                    "workflow_completed_steps",
                    value=float(completed_steps),
                    scope=MetricScope.WORKFLOW,
                )

            if planning_info is not None:
                self.metric_engine.observe(
                    metric_ctx,
                    "estimated_tokens",
                    float(planning_info.get("estimated_tokens", 0)),
                    metric_type=MetricType.HISTOGRAM,
                    scope=MetricScope.RUNTIME,
                )

            metrics_result = self.metric_engine.collect(metric_ctx)
            logger.info(
                "Metrics: %d records collected",
                metrics_result.count,
            )

        # 12. Result
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
            memory={
                "retrieve": memory_retrieve_info,
                "store": memory_store_info,
            }
            if self.memory_engine is not None
            else None,
            metrics=metrics_result,
            reliability=reliability_info,
        )
