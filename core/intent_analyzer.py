import re


class IntentAnalyzer:

    def analyze(self, query: str):

        query_lower = query.lower()

        # -------------------------
        # 1. Compare Intent
        # -------------------------
        compare_keywords = ["vs", "compare", "对比", "比较", "versus", "和.*哪个", "与.*哪个"]
        is_compare = any(
            kw in query_lower if ".*" not in kw else re.search(kw, query_lower)
            for kw in compare_keywords
        )

        if is_compare:
            companies = self._extract_companies(query)
            return {
                "intent": "COMPARE_COMPANIES",
                "companies": companies,
                "document_ids": None
            }

        # -------------------------
        # 2. Single Company Intent
        # -------------------------
        companies = self._extract_companies(query)

        if len(companies) == 1:
            return {
                "intent": "SINGLE_COMPANY",
                "companies": companies,
                "document_ids": None
            }

        # -------------------------
        # 3. Global Intent
        # -------------------------
        if len(companies) == 0:
            return {
                "intent": "GLOBAL_RESEARCH",
                "companies": None,
                "document_ids": None
            }

        return {
            "intent": "UNKNOWN",
            "companies": companies,
            "document_ids": None
        }

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
