import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from unittest.mock import MagicMock

import pytest

from agent.agent_runtime import AgentRuntime
from agent.execution_plan import ExecutionPlan, PlanStep, StepStatus, StepType
from agent.execution_result import ExecutionResult
from agent.reasoning_models import Evidence, ReasoningResult
from agent.runtime_result import RuntimeResult


class FakeRetriever:
    def retrieve_evidence(self, context, store):
        return [
            Evidence(
                content="Revenue grew 10% year over year.",
                source="apple.pdf",
                company=context.company or "Unknown",
                confidence=0.95,
                metadata={"chunk_id": "apple_0"},
            ),
        ]


class FakeIntentAnalyzer:
    def analyze(self, query):
        return {
            "intent": "SINGLE_COMPANY",
            "companies": ["Apple"],
        }


class FakePlanner:
    def plan(self, query, intent):
        return ExecutionPlan(
            intent="single_company",
            original_query=query,
            tasks=[
                PlanStep(
                    step_id=1,
                    step_type=StepType.RETRIEVE,
                    description="Retrieve Apple financial report",
                    company="Apple",
                    query=query,
                ),
                PlanStep(
                    step_id=2,
                    step_type=StepType.SYNTHESIS,
                    description="Synthesize findings",
                    depends_on=[1],
                ),
            ],
        )


class FakeReasoner:
    def analyze(self, results):
        return ReasoningResult(
            facts=["Revenue grew 10%."],
            risks=[],
            opportunities=["Strong growth."],
            conclusion="Collected 1 financial facts, 0 risk signals, and 1 opportunity signals.",
        )


class FakeExecutor:
    def __init__(self):
        self._handlers = {}

    def register_handler(self, step_type, handler):
        self._handlers[step_type] = handler

    def execute(self, plan, shared):
        for step in plan.tasks:
            handler = self._handlers.get(step.step_type)
            if handler:
                try:
                    output = handler(step, shared)
                    step.status = StepStatus.COMPLETED
                    step.result = ExecutionResult(
                        step_id=step.step_id,
                        success=True,
                        output=output,
                    )
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.result = ExecutionResult(
                        step_id=step.step_id,
                        success=False,
                        error=str(e),
                    )
        return plan


class TestAgentRuntime:
    @pytest.fixture
    def runtime(self):
        retriever = FakeRetriever()
        planner = FakePlanner()
        executor = FakeExecutor()
        reasoner = FakeReasoner()
        intent_analyzer = FakeIntentAnalyzer()

        def retrieve_handler(step, shared):
            ctx = MagicMock()
            ctx.question = step.query
            ctx.company = step.company
            evidences = retriever.retrieve_evidence(ctx, None)
            shared.setdefault("_all_evidence", []).extend(evidences)
            return evidences

        executor.register_handler(StepType.RETRIEVE, retrieve_handler)
        executor.register_handler(StepType.SYNTHESIS, lambda s, c: None)

        return AgentRuntime(
            planner=planner,
            executor=executor,
            reasoner=reasoner,
            retriever=retriever,
            intent_analyzer=intent_analyzer,
        )

    def test_run_returns_runtime_result(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert isinstance(result, RuntimeResult)
        assert result.context is not None
        assert result.citations is not None
        assert result.evidence is not None
        assert result.plan is not None
        assert result.intent_result is not None
        assert result.reasoning_result is not None

    def test_run_with_company(self, runtime):
        result = runtime.run("Revenue analysis", company="Apple")
        assert isinstance(result, RuntimeResult)

    def test_run_produces_evidence(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert len(result.evidence) >= 1
        assert result.evidence[0].source == "apple.pdf"

    def test_run_produces_citations(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert len(result.citations) >= 1
        assert result.citations[0]["source"] == "apple.pdf"

    def test_run_produces_context(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert "Evidence 1" in result.context
        assert "apple.pdf" in result.context

    def test_run_produces_plan(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert result.plan.intent == "single_company"
        assert len(result.plan.tasks) == 2

    def test_run_produces_intent_result(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert result.intent_result["intent"] == "SINGLE_COMPANY"
        assert "Apple" in result.intent_result["companies"]

    def test_run_produces_reasoning_result(self, runtime):
        result = runtime.run("What is Apple revenue?")
        assert "Revenue grew" in result.reasoning_result.facts[0]
        assert result.reasoning_result.conclusion != ""
