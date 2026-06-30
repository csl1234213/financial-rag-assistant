# ============================================================
# Entity Extractor — Company & Year Extraction
# ============================================================
# Simple rule-based entity extraction for the first version.
# Later versions can add NER (spaCy / LLM) without changing
# the extractor interface.
# ============================================================

import re


_COMPANY_MAP = {
    "apple": "Apple",
    "苹果": "Apple",
    "tesla": "Tesla",
    "特斯拉": "Tesla",
    "nvidia": "NVIDIA",
    "英伟达": "NVIDIA",
    "amd": "AMD",
    "超威": "AMD",
    "microsoft": "Microsoft",
    "微软": "Microsoft",
    "google": "Google",
    "alphabet": "Alphabet",
    "谷歌": "Google",
    "amazon": "Amazon",
    "亚马逊": "Amazon",
    "meta": "Meta",
    "facebook": "Meta",
    "netflix": "Netflix",
    "奈飞": "Netflix",
    "intel": "Intel",
    "英特尔": "Intel",
    "tsmc": "TSMC",
    "台积电": "TSMC",
    "samsung": "Samsung",
    "三星": "Samsung",
    "qualcomm": "Qualcomm",
    "高通": "Qualcomm",
    "broadcom": "Broadcom",
    "博通": "Broadcom",
    "jpmorgan": "JPMorgan",
    "摩根大通": "JPMorgan",
    "berkshire": "Berkshire Hathaway",
    "伯克希尔": "Berkshire Hathaway",
    "visa": "Visa",
    "mastercard": "Mastercard",
    "万事达": "Mastercard",
    "walmart": "Walmart",
    "沃尔玛": "Walmart",
    "cocacola": "Coca-Cola",
    "coca-cola": "Coca-Cola",
    "可口可乐": "Coca-Cola",
    "pepsi": "Pepsi",
    "百事": "Pepsi",
    "disney": "Disney",
    "迪士尼": "Disney",
    "toyota": "Toyota",
    "丰田": "Toyota",
    "alibaba": "Alibaba",
    "阿里巴巴": "Alibaba",
    "tencent": "Tencent",
    "腾讯": "Tencent",
    "byd": "BYD",
    "比亚迪": "BYD",
    "huawei": "Huawei",
    "华为": "Huawei",
    "xiaomi": "Xiaomi",
    "小米": "Xiaomi",
    "baidu": "Baidu",
    "百度": "Baidu",
    "jd": "JD.com",
    "京东": "JD.com",
    "pdd": "Pinduoduo",
    "拼多多": "Pinduoduo",
    "meituan": "Meituan",
    "美团": "Meituan",
    "netease": "NetEase",
    "网易": "NetEase",
}

_YEAR_PATTERN = re.compile(r"\b(20[012]\d)\b")


def extract_companies(question: str) -> list[str]:
    lower = question.lower()
    seen: set[str] = set()
    result: list[str] = []

    for key, name in _COMPANY_MAP.items():
        if key in lower and name not in seen:
            seen.add(name)
            result.append(name)

    return result


def extract_years(question: str) -> list[str]:
    matches = _YEAR_PATTERN.findall(question)
    seen: set[str] = set()
    result: list[str] = []

    for year in matches:
        if year not in seen:
            seen.add(year)
            result.append(year)

    return result