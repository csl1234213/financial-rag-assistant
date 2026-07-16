from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent.execution_plan import ExecutionPlan
from agent.reasoning_models import Evidence, ReasoningResult

if TYPE_CHECKING:
    from agent.metrics.metric_result import MetricResult


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

    execution: Optional[Dict[str, Any]] = None

    workflow: Optional[Dict[str, Any]] = None

    memory: Optional[Dict[str, Any]] = None

    metrics: Optional["MetricResult"] = None

    reliability: Optional[Dict[str, Any]] = None
