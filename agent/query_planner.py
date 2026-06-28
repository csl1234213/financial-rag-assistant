from agent.execution_plan import ExecutionPlan, PlanStep, StepType


class QueryPlanner:
    """
    V3 Query Planner
    将用户问题拆解为可执行 AI 任务流，返回结构化 ExecutionPlan
    """

    def __init__(self):
        self._step_counter = 1

    def _next_id(self):
        sid = self._step_counter
        self._step_counter += 1
        return sid

    def _reset_counter(self):
        self._step_counter = 1

    # =========================
    # Main Entry
    # =========================
    def plan(self, query: str, intent: dict) -> ExecutionPlan:
        self._reset_counter()

        intent_type = intent.get("intent", "UNKNOWN")
        companies = intent.get("companies", [])

        if intent_type == "COMPARE_COMPANIES":
            return self._build_compare_plan(query, companies)

        elif intent_type == "SINGLE_COMPANY":
            return self._build_single_plan(query, companies)

        elif intent_type == "GLOBAL_RESEARCH":
            return self._build_global_plan(query)

        else:
            return self._build_generic_plan(query)

    # =========================
    # 1. Compare Plan
    # =========================
    def _build_compare_plan(self, query, companies) -> ExecutionPlan:

        plan = ExecutionPlan(
            intent="comparison",
            original_query=query
        )

        retrieve_ids = []

        for c in companies:
            step = PlanStep(
                step_id=self._next_id(),
                step_type=StepType.RETRIEVE,
                description=f"Retrieve {c} financial report",
                company=c,
                query=query,
                parameters={"metrics": ["revenue", "margin", "risk"]}
            )
            plan.tasks.append(step)
            retrieve_ids.append(step.step_id)

        compare_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.COMPARE,
            description="Compare financial metrics across companies",
            depends_on=retrieve_ids,
            parameters={"metrics": ["revenue", "margin", "risk"]}
        )
        plan.tasks.append(compare_step)

        synthesis_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.SYNTHESIS,
            description="Synthesize comparison findings",
            depends_on=[compare_step.step_id]
        )
        plan.tasks.append(synthesis_step)

        return plan

    # =========================
    # 2. Single Company Plan
    # =========================
    def _build_single_plan(self, query, companies) -> ExecutionPlan:

        company = companies[0] if companies else None

        plan = ExecutionPlan(
            intent="single_company",
            original_query=query
        )

        retrieve_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.RETRIEVE,
            description=f"Retrieve {company} financial report",
            company=company,
            query=query,
            parameters={"metrics": ["revenue", "profit", "risk"]}
        )
        plan.tasks.append(retrieve_step)

        synthesis_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.SYNTHESIS,
            description="Synthesize research findings",
            depends_on=[retrieve_step.step_id]
        )
        plan.tasks.append(synthesis_step)

        return plan

    # =========================
    # 3. Global Plan
    # =========================
    def _build_global_plan(self, query) -> ExecutionPlan:

        plan = ExecutionPlan(
            intent="global_research",
            original_query=query
        )

        retrieve_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.RETRIEVE,
            description="Retrieve relevant documents",
            query=query
        )
        plan.tasks.append(retrieve_step)

        synthesis_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.SYNTHESIS,
            description="Synthesize research findings",
            depends_on=[retrieve_step.step_id]
        )
        plan.tasks.append(synthesis_step)

        return plan

    # =========================
    # 4. Fallback Plan
    # =========================
    def _build_generic_plan(self, query) -> ExecutionPlan:

        plan = ExecutionPlan(
            intent="generic",
            original_query=query
        )

        retrieve_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.RETRIEVE,
            description="Retrieve relevant documents",
            query=query
        )
        plan.tasks.append(retrieve_step)

        synthesis_step = PlanStep(
            step_id=self._next_id(),
            step_type=StepType.SYNTHESIS,
            description="Synthesize findings",
            depends_on=[retrieve_step.step_id]
        )
        plan.tasks.append(synthesis_step)

        return plan
