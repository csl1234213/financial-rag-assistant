from typing import Any, Dict, List


def retrieval_score(sources: List[Dict[str, Any]], expected_sources: List[str]) -> float:
    if not expected_sources:
        return 100.0

    source_urls = set()
    for s in sources:
        if isinstance(s, dict):
            url = s.get("url", "") or s.get("source", "")
        else:
            url = str(s)
        if url:
            source_urls.add(url.lower().rstrip("/"))

    expected_urls = set(u.lower().rstrip("/") for u in expected_sources)

    if not expected_urls:
        return 100.0 if source_urls else 0.0

    matched = source_urls & expected_urls

    recall = len(matched) / len(expected_urls) if expected_urls else 0.0
    precision = len(matched) / len(source_urls) if source_urls else 0.0

    if matched:
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    else:
        f1 = 0.0

    return round(f1 * 100, 1)


def tool_selection_score(tools_used: List[str], expected_tools: List[str]) -> float:
    if not expected_tools:
        return 100.0

    used_set = set(t.strip().lower() for t in tools_used)
    expected_set = set(t.strip().lower() for t in expected_tools)

    matched = used_set & expected_set

    recall = len(matched) / len(expected_set) if expected_set else 0.0
    precision = len(matched) / len(used_set) if used_set else 0.0

    if matched:
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    else:
        f1 = 0.0

    return round(f1 * 100, 1)


def answer_quality_score(
    answer: str,
    question: str,
    criteria: List[str],
) -> float:
    if not answer or not answer.strip():
        return 0.0

    answer_lower = answer.lower()
    question_lower = question.lower()

    scores = []

    if len(answer) >= 20:
        scores.append(1.0)
    elif len(answer) >= 10:
        scores.append(0.5)
    else:
        scores.append(0.0)

    if len(answer) >= 100:
        scores.append(1.0)
    elif len(answer) >= 50:
        scores.append(0.5)
    else:
        scores.append(0.0)

    covered_criteria = 0
    for criterion in criteria:
        criterion_lower = criterion.lower()
        if criterion_lower in answer_lower:
            covered_criteria += 1.0
        else:
            keywords = criterion_lower.replace("_", " ").split()
            if any(kw in answer_lower for kw in keywords):
                covered_criteria += 0.5

    if criteria:
        criteria_score = covered_criteria / len(criteria)
    else:
        criteria_score = 1.0
    scores.append(min(criteria_score, 1.0))

    fallback_markers = [
        "unable to process",
        "fallback",
        "not available",
        "cannot process",
        "error",
    ]
    if any(marker in answer_lower for marker in fallback_markers):
        scores.append(0.0)
    else:
        scores.append(1.0)

    return round(sum(scores) / len(scores) * 100, 1)


def hallucination_score(
    answer: str,
    sources: List[Dict[str, Any]],
    companies: List[str],
) -> float:
    if not answer or not answer.strip():
        return 100.0

    score = 100.0
    answer_lower = answer.lower()

    hallucination_markers = [
        "guaranteed return",
        "risk-free",
        "insider information",
        "secret deal",
        "confidential source",
        "100% guaranteed",
        "perfect prediction",
    ]

    found_markers = 0
    for marker in hallucination_markers:
        if marker in answer_lower:
            found_markers += 1
            score -= 10.0

    if sources:
        score = min(score + 5.0, 100.0)

    if companies:
        company_names_in_answer = 0
        for company in companies:
            if company.lower() in answer_lower:
                company_names_in_answer += 1
        if company_names_in_answer > 0:
            score = min(score + 5.0, 100.0)

    score = max(score, 0.0)
    return round(score, 1)


def calculate_overall_score(
    retrieval_s: float,
    tool_s: float,
    quality_s: float,
    hallucination_s: float,
    weights: Dict[str, float] = None,
) -> float:
    if weights is None:
        weights = {
            "retrieval": 0.25,
            "tool": 0.20,
            "quality": 0.35,
            "hallucination": 0.20,
        }

    overall = (
        retrieval_s * weights["retrieval"]
        + tool_s * weights["tool"]
        + quality_s * weights["quality"]
        + hallucination_s * weights["hallucination"]
    )

    return round(overall, 1)