import re

from agent.planning.entity_extractor import extract_companies as _extract_company_entities

# Financial/research keywords that indicate a query is research-oriented
# rather than a simple chat. Without these, the query is DIRECT_CHAT.
_RESEARCH_SIGNALS = [
    "revenue",
    "profit",
    "margin",
    "ebitda",
    "earnings",
    "eps",
    "balance sheet",
    "income statement",
    "cash flow",
    "market cap",
    "dividend",
    "risk",
    "growth",
    "trend",
    "forecast",
    "outlook",
    "strategy",
    "analysis",
    "analyze",
    "research",
    "financial",
    "investment",
    "sector",
    "industry",
    "market",
    "stock",
    "price",
    "economy",
    "economic",
    "interest rate",
    "inflation",
    "gdp",
    "营收",
    "利润",
    "净利润",
    "毛利率",
    "现金流",
    "股息",
    "市盈率",
    "分析",
    "研究",
    "风险",
    "增长",
    "趋势",
    "投资",
    "市场",
    "行业",
    "财务",
    "经济",
]

_GENERAL_CONCEPT_PREFIX = re.compile(
    r"^(?:please\s+)?(?:(?:what is\b)|what does\b.*\bmean\b|explain\b|define\b|"
    r"describe the difference\b)"
    r"|^(?:请)?(?:什么是|什么叫|解释|说明|简单解释|用简单|简单说)"
)
_SOURCE_REFERENCE = re.compile(
    r"\b(?:reports?|filings?|documents?|uploaded|10-[kq])\b|财报|财务报告|年报|季报|上传|文档"
)


class IntentAnalyzer:
    def analyze(self, query: str):
        query_lower = query.lower()

        # -------------------------
        # 1. Compare Intent
        # -------------------------
        compare_keywords = ["vs", "compare", "对比", "比较", "versus", "和.*哪个", "与.*哪个"]
        is_compare = any(kw in query_lower if ".*" not in kw else re.search(kw, query_lower) for kw in compare_keywords)

        if is_compare:
            companies = self._extract_companies(query)
            return {"intent": "COMPARE_COMPANIES", "companies": companies, "document_ids": None}

        # -------------------------
        # 2. Single Company Intent
        # -------------------------
        companies = self._extract_companies(query)

        if len(companies) == 1:
            return {"intent": "SINGLE_COMPANY", "companies": companies, "document_ids": None}

        # -------------------------
        # 3. Multiple companies without compare keyword
        # -------------------------
        if len(companies) > 1:
            return {"intent": "UNKNOWN", "companies": companies, "document_ids": None}

        # -------------------------
        # 4. No companies — direct chat vs research
        # -------------------------
        if self._is_direct_chat(query_lower):
            return {"intent": "DIRECT_CHAT", "companies": None, "document_ids": None}

        return {"intent": "GLOBAL_RESEARCH", "companies": None, "document_ids": None}

    def _is_direct_chat(self, query_lower: str) -> bool:
        # A definition/explanation without a named company or source should
        # be answered conversationally, even when it contains a financial
        # term such as "gross margin"/"毛利率".
        if (
            _GENERAL_CONCEPT_PREFIX.search(query_lower.strip())
            and not self._extract_companies(query_lower)
            and not _SOURCE_REFERENCE.search(query_lower)
        ):
            return True
        for signal in _RESEARCH_SIGNALS:
            if signal in query_lower:
                return False
        return True

    def _extract_companies(self, query: str):
        # Keep the runtime intent router aligned with the planner's canonical
        # aliases; separate maps caused implicit bilingual issuer descriptions
        # (for example, "iPhone maker") to fall through to direct chat.
        return _extract_company_entities(query)
