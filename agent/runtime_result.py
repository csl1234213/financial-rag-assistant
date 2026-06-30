from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.execution_plan import ExecutionPlan
from agent.reasoning_models import Evidence, ReasoningResult


@dataclass
class RuntimeResult:
    """
    Unified output produced by one AgentRuntime.run() call.

    UI / API consumes exactly one object, not a long tuple.
    """

    reasoning_result: Optional[ReasoningResult] = None

    context: str = ""

    citations: List[Dict[str, Any]] = field(default_factory=list)

    report: str = ""

    evidence: List[Evidence] = field(default_factory=list)

    plan: Optional[ExecutionPlan] = None

    intent_result: Dict[str, Any] = field(default_factory=dict)

    routing: Optional[Dict[str, Any]] = None

    planning: Optional[Dict[str, Any]] = None