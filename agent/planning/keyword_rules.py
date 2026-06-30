# ============================================================
# Keyword Rules — Task Classification Keywords
# ============================================================
# All keyword lists are centralized here so that:
# 1. TaskAnalyzer stays clean (no keyword clutter)
# 2. Adding a new keyword never touches Analyzer code
# 3. Keywords can be reviewed and tuned independently
# ============================================================

from .task_enums import TaskType

# =========================
# Keyword Lists
# =========================

OCR_KEYWORDS = [
    "ocr",
    "scan",
    "扫描",
    "识别",
]

IMAGE_ANALYSIS_KEYWORDS = [
    "image",
    "photo",
    "picture",
    "chart",
    "图片",
    "截图",
    "图表",
]

COMPARISON_KEYWORDS = [
    "compare",
    "comparison",
    "vs",
    "versus",
    "比较",
    "对比",
]

DOCUMENT_QA_KEYWORDS = [
    "10-k",
    "10-q",
    "annual report",
    "annual reports",
    "financial report",
    "financial statement",
    "filing",
    "财报",
    "年报",
    "季报",
    "财务报告",
    "risk factor",
    "risk factors",
    "risk",
    "revenue",
    "profit",
    "margin",
    "ebitda",
    "balance sheet",
    "income statement",
    "cash flow",
    "cap",
    "market cap",
    "dividend",
    "earnings",
    "eps",
    "p/e",
    "pe ratio",
    "增长率",
    "营收",
    "利润",
    "净利润",
    "毛利率",
    "净利率",
    "现金流",
    "股息",
    "市盈率",
    "市净率",
]

RESEARCH_KEYWORDS = [
    "research",
    "analyze",
    "analysis",
    "研究",
    "深入",
    "分析",
    "deep dive",
    "deep research",
    "investigate",
    "调查",
    "调研",
    "评估",
    "assessment",
    "展望",
    "outlook",
    "forecast",
    "预测",
    "trend",
    "趋势",
    "strategy",
    "战略",
    "market",
    "industry",
    "行业",
    "sector",
]

# =========================
# Priority-ordered lookup
# =========================
# Higher priority rules are checked first to avoid
# misclassification (e.g. "analyze this image" → RESEARCH
# would be wrong; it should be IMAGE_ANALYSIS).

_PRIORITY_ORDER = [
    (TaskType.OCR, OCR_KEYWORDS),
    (TaskType.IMAGE_ANALYSIS, IMAGE_ANALYSIS_KEYWORDS),
    (TaskType.COMPARISON, COMPARISON_KEYWORDS),
    (TaskType.DOCUMENT_QA, DOCUMENT_QA_KEYWORDS),
    (TaskType.RESEARCH, RESEARCH_KEYWORDS),
]


def classify_by_keyword(question_lower: str) -> tuple[TaskType, str | None]:
    for task_type, keywords in _PRIORITY_ORDER:
        for kw in keywords:
            if kw in question_lower:
                return task_type, kw
    return TaskType.CHAT, None