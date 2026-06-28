import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from agent.execution_plan import ExecutionPlan, StepType
from agent.query_planner import QueryPlanner


class TestQueryPlanner:
    @pytest.fixture
    def planner(self):
        return QueryPlanner()

    def test_compare_companies_plan(self, planner):
        intent = {
            "intent": "COMPARE_COMPANIES",
            "companies": ["Apple", "Tesla"],
        }
        plan = planner.plan("Compare Apple and Tesla revenue", intent)
        assert isinstance(plan, ExecutionPlan)
        assert plan.intent == "comparison"
        assert plan.original_query == "Compare Apple and Tesla revenue"

        step_types = [t.step_type for t in plan.tasks]
        assert StepType.RETRIEVE in step_types
        assert StepType.COMPARE in step_types
        assert StepType.SYNTHESIS in step_types

        retrieve_steps = [t for t in plan.tasks if t.step_type == StepType.RETRIEVE]
        assert len(retrieve_steps) == 2
        companies = {t.company for t in retrieve_steps}
        assert companies == {"Apple", "Tesla"}

        compare_step = [t for t in plan.tasks if t.step_type == StepType.COMPARE][0]
        assert len(compare_step.depends_on) == 2

        synthesis_step = [t for t in plan.tasks if t.step_type == StepType.SYNTHESIS][0]
        assert compare_step.step_id in synthesis_step.depends_on

    def test_single_company_plan(self, planner):
        intent = {
            "intent": "SINGLE_COMPANY",
            "companies": ["Apple"],
        }
        plan = planner.plan("Apple revenue analysis", intent)
        assert isinstance(plan, ExecutionPlan)
        assert plan.intent == "single_company"

        step_types = [t.step_type for t in plan.tasks]
        assert StepType.RETRIEVE in step_types
        assert StepType.SYNTHESIS in step_types

        retrieve_step = [t for t in plan.tasks if t.step_type == StepType.RETRIEVE][0]
        assert retrieve_step.company == "Apple"

    def test_single_company_no_company(self, planner):
        intent = {
            "intent": "SINGLE_COMPANY",
            "companies": [],
        }
        plan = planner.plan("Revenue analysis", intent)
        assert isinstance(plan, ExecutionPlan)
        retrieve_step = [t for t in plan.tasks if t.step_type == StepType.RETRIEVE][0]
        assert retrieve_step.company is None

    def test_global_research_plan(self, planner):
        intent = {
            "intent": "GLOBAL_RESEARCH",
            "companies": None,
        }
        plan = planner.plan("Market trends analysis", intent)
        assert isinstance(plan, ExecutionPlan)
        assert plan.intent == "global_research"

        step_types = [t.step_type for t in plan.tasks]
        assert StepType.RETRIEVE in step_types
        assert StepType.SYNTHESIS in step_types

    def test_generic_fallback_plan(self, planner):
        intent = {
            "intent": "UNKNOWN",
            "companies": [],
        }
        plan = planner.plan("Hello", intent)
        assert isinstance(plan, ExecutionPlan)
        assert plan.intent == "generic"

        step_types = [t.step_type for t in plan.tasks]
        assert StepType.RETRIEVE in step_types
        assert StepType.SYNTHESIS in step_types

    def test_step_ids_are_sequential(self, planner):
        intent = {"intent": "COMPARE_COMPANIES", "companies": ["Apple", "Tesla"]}
        plan = planner.plan("Compare", intent)
        ids = [t.step_id for t in plan.tasks]
        assert ids == sorted(ids)
        assert ids[0] == 1

    def test_step_counter_resets(self, planner):
        intent1 = {"intent": "SINGLE_COMPANY", "companies": ["Apple"]}
        plan1 = planner.plan("Q1", intent1)
        assert plan1.tasks[0].step_id == 1

        intent2 = {"intent": "SINGLE_COMPANY", "companies": ["Tesla"]}
        plan2 = planner.plan("Q2", intent2)
        assert plan2.tasks[0].step_id == 1
