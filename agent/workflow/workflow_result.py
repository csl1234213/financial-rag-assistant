# ============================================================
# Workflow Result
# ============================================================
# Unified output of the Workflow Layer.
# 描述一个完整 Workflow 的结构 — 类型、步骤列表、
# 预估耗时、所需能力、置信度。
#
# 不包含 Provider（模型选择是 Routing 的职责）。
# ============================================================

from dataclasses import dataclass, field
from typing import List, Optional

from .workflow_enums import WorkflowType
from .workflow_models import WorkflowStep


@dataclass(slots=True)
class WorkflowResult:
    workflow: WorkflowType

    steps: List[WorkflowStep] = field(default_factory=list)

    estimated_time_ms: int = 0

    requires_tools: bool = False

    requires_memory: bool = False

    requires_human: bool = False

    confidence: float = 1.0

    reason: str = ""

    next_workflow: Optional[WorkflowType] = None