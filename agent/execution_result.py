from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionResult:
    """
    Unified result produced by executing one PlanStep.
    """

    step_id: int

    success: bool

    output: Any = None

    error: Optional[str] = None

    routing: Optional[Dict[str, Any]] = None