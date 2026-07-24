from typing import Any, Dict, List, Optional

from evaluation.metrics import (
    answer_quality_score,
    calculate_overall_score,
    hallucination_score,
    retrieval_score,
    tool_selection_score,
)


def evaluate_agent_response(
    answer: str,
    question: str,
    tools_used: List[str],
    sources: List[Dict[str, Any]],
    companies: List[str],
    expected_tools: List[str],
    expected_sources: List[str],
    criteria: List[str],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    retrieval_s = retrieval_score(sources, expected_sources)
    tool_s = tool_selection_score(tools_used, expected_tools)
    quality_s = answer_quality_score(answer, question, criteria)
    hallucination_s = hallucination_score(answer, sources, companies)

    overall = calculate_overall_score(
        retrieval_s=retrieval_s,
        tool_s=tool_s,
        quality_s=quality_s,
        hallucination_s=hallucination_s,
        weights=weights,
    )

    issues = []

    if retrieval_s < 50:
        issues.append({
            "type": "retrieval",
            "severity": "high" if retrieval_s < 30 else "medium",
            "message": f"Low retrieval score ({retrieval_s}): expected {expected_sources}, got {len(sources)} sources",
        })

    if tool_s < 50:
        issues.append({
            "type": "tool_selection",
            "severity": "high" if tool_s < 30 else "medium",
            "message": f"Low tool selection score ({tool_s}): expected {expected_tools}, used {tools_used}",
        })

    if quality_s < 40:
        issues.append({
            "type": "answer_quality",
            "severity": "high",
            "message": f"Low answer quality score ({quality_s}): answer may be too short or incomplete",
        })
    elif quality_s < 60:
        issues.append({
            "type": "answer_quality",
            "severity": "medium",
            "message": f"Moderate answer quality score ({quality_s}): consider improving completeness",
        })

    if hallucination_s < 70:
        issues.append({
            "type": "hallucination",
            "severity": "high",
            "message": f"Hallucination risk detected (score: {hallucination_s})",
        })

    if not answer or not answer.strip():
        issues.append({
            "type": "empty_response",
            "severity": "critical",
            "message": "Agent returned empty response",
        })

    fallback_markers = ["unable to process", "fallback", "cannot process"]
    if any(marker in answer.lower() for marker in fallback_markers):
        issues.append({
            "type": "fallback",
            "severity": "high",
            "message": "Agent used fallback response",
        })

    return {
        "score": overall,
        "retrieval_score": retrieval_s,
        "tool_score": tool_s,
        "quality_score": quality_s,
        "hallucination_score": hallucination_s,
        "issues": issues,
        "passed": overall >= 60.0 and len([i for i in issues if i["severity"] in ("critical", "high")]) == 0,
    }


def evaluate_batch(
    results: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    if not results:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "average_score": 0.0,
            "results": [],
        }

    passed = sum(1 for r in results if r.get("passed", False))
    failed = len(results) - passed
    avg_score = sum(r.get("score", 0.0) for r in results) / len(results)

    metric_averages = {}
    for key in ("retrieval_score", "tool_score", "quality_score", "hallucination_score"):
        values = [r.get(key, 0.0) for r in results if key in r]
        if values:
            metric_averages[key] = round(sum(values) / len(values), 1)

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "average_score": round(avg_score, 1),
        "metric_averages": metric_averages,
        "results": results,
    }