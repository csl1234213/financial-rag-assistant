import re

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
        for signal in _RESEARCH_SIGNALS:
            if signal in query_lower:
                return False
        return True

    def _extract_companies(self, query: str):
        companies = []

        keywords = {
            "apple": "Apple",
            "苹果": "Apple",
            "tesla": "Tesla",
            "特斯拉": "Tesla",
            "nvidia": "NVIDIA",
            "英伟达": "NVIDIA",
            "amd": "AMD",
            "超威": "AMD",
        }

        for k, v in keywords.items():
            if k in query.lower():
                companies.append(v)

        return companies
