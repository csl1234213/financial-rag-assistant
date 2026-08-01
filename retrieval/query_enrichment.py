"""Deterministic multilingual query hints for English financial filings.

The local embedding model supports multilingual retrieval, but short Chinese
questions and conversational English requests can still underspecify the exact
terminology used in SEC-style tables.  This module appends a small, auditable
finance glossary to the retrieval-only query.  The original user question
remains unchanged for planning, prompting, logging, and display.
"""

from __future__ import annotations

import re

_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
_FISCAL_QUARTER_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*财年.{0,8}?第(?P<quarter>[一二三四])季度"
)
_CALENDAR_QUARTER_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*年.{0,8}?第(?P<quarter>[一二三四])季度"
)
_ENGLISH_QUARTER_PATTERN = re.compile(
    r"\bQ(?P<quarter>[1-4])(?:\s*[-/'’]\s*|\s+)"
    r"(?P<year>20\d{2}|\d{2})\b",
    flags=re.IGNORECASE,
)
_QUARTER_NUMBER = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
}

_COMPANY_HINTS = {
    "apple": "Apple",
    "nvidia": "NVIDIA",
    "tesla": "Tesla",
}

_ALIASES = (
    ("英伟达", "NVIDIA"),
    ("辉达", "NVIDIA"),
    ("特斯拉", "Tesla"),
    ("苹果", "Apple"),
)

# Longest and most specific expressions come first.  Keeping phrases intact
# gives both E5 and BM25 the terminology that appears in English filings.
_FINANCIAL_HINTS = (
    ("经营活动现金流", "operating cash flow"),
    ("自由现金流", "free cash flow"),
    ("汽车业务", "automotive"),
    ("服务业务", "services"),
    ("营业利润", "operating income"),
    ("净利润", "net income"),
    ("毛利率", "gross margin"),
    ("毛利润", "gross profit"),
    ("总收入", "total revenue"),
    ("第一季度", "Q1 first quarter"),
    ("第二季度", "Q2 second quarter"),
    ("第三季度", "Q3 third quarter"),
    ("第四季度", "Q4 fourth quarter"),
    ("现金流", "cash flow"),
    ("毛利", "gross profit"),
    ("营收", "revenue"),
    ("收入", "revenue"),
    ("利润", "profit"),
    ("财年", "fiscal year"),
    ("同比", "year over year"),
    ("环比", "quarter over quarter"),
    ("增速", "growth rate"),
    ("增长", "growth"),
    ("下降", "decline"),
)

_ENGLISH_FINANCIAL_HINTS = (
    (
        re.compile(
            r"\bautomotive\s+(?:business\s+)?revenue(?:s)?\b",
            flags=re.IGNORECASE,
        ),
        "total automotive revenues",
    ),
    (
        re.compile(
            r"\bservices?\s+(?:business\s+)?revenue(?:s)?\b",
            flags=re.IGNORECASE,
        ),
        "services and other revenue",
    ),
    (
        re.compile(
            r"(?:\brevenue(?:s)?\s+(?:growth|trend)\b|"
            r"\b(?:growth|trend)\s+(?:in\s+)?revenue(?:s)?\b)",
            flags=re.IGNORECASE,
        ),
        "quarterly total revenues",
    ),
)


def enrich_financial_query(question: str, company: str | None = None) -> str:
    """Append canonical filing terms to a multilingual financial question."""

    normalized = question.strip()
    if not normalized:
        return normalized

    hints: list[str] = []
    seen: set[str] = set()

    def add_hint(hint: str) -> None:
        key = hint.casefold()
        if key not in seen and key not in normalized.casefold():
            seen.add(key)
            hints.append(hint)

    if company:
        company_hint = _COMPANY_HINTS.get(company.strip().casefold())
        if company_hint:
            add_hint(company_hint)

    if _CJK_PATTERN.search(normalized):
        for alias, hint in _ALIASES:
            if alias in normalized:
                add_hint(hint)

        for match in _FISCAL_QUARTER_PATTERN.finditer(normalized):
            year = match.group("year")
            quarter = _QUARTER_NUMBER[match.group("quarter")]
            add_hint(f"Q{quarter} FY{year[-2:]}")
            add_hint(f"Q{quarter} Fiscal {year}")

        for match in _CALENDAR_QUARTER_PATTERN.finditer(normalized):
            year = match.group("year")
            quarter = _QUARTER_NUMBER[match.group("quarter")]
            add_hint(f"Q{quarter} {year}")
            add_hint(f"Q{quarter}-{year}")

        for phrase, hint in _FINANCIAL_HINTS:
            if phrase in normalized:
                add_hint(hint)

    for match in _ENGLISH_QUARTER_PATTERN.finditer(normalized):
        quarter = match.group("quarter")
        year = match.group("year")
        full_year = year if len(year) == 4 else f"20{year}"
        add_hint(f"Q{quarter}-{full_year}")
        add_hint(f"Q{quarter}'{full_year[-2:]}")

    for pattern, hint in _ENGLISH_FINANCIAL_HINTS:
        if pattern.search(normalized):
            add_hint(hint)

    if not hints:
        return normalized
    return f"{normalized} {' '.join(hints)}"
