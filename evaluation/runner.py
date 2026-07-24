import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.evaluator import evaluate_agent_response, evaluate_batch
from services.agent_runtime.runtime import run_agent

logger = logging.getLogger(__name__)

_DATASET_DIR = Path(__file__).resolve().parent / "datasets"
_REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def load_dataset(dataset_name: str = "financial_qa.json") -> List[Dict[str, Any]]:
    dataset_path = _DATASET_DIR / dataset_name
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Dataset must be a list, got {type(data)}")

    logger.info(f"Loaded {len(data)} questions from {dataset_name}")
    return data


def run_single_evaluation(
    question: str,
    expected_tools: List[str],
    expected_sources: List[str],
    criteria: List[str],
    thread_id: str = "eval",
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    t0 = time.time()
    result = run_agent(
        question=question,
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    duration = round(time.time() - t0, 3)

    evaluation = evaluate_agent_response(
        answer=result.get("answer", ""),
        question=question,
        tools_used=result.get("tools_used", []),
        sources=result.get("sources", []),
        companies=result.get("companies", []),
        expected_tools=expected_tools,
        expected_sources=expected_sources,
        criteria=criteria,
    )

    return {
        "question": question,
        "answer": result.get("answer", ""),
        "tools_used": result.get("tools_used", []),
        "sources": result.get("sources", []),
        "companies": result.get("companies", []),
        "duration": duration,
        "evaluation": evaluation,
    }


def run_dataset_evaluation(
    dataset_name: str = "financial_qa.json",
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    dataset = load_dataset(dataset_name)

    if limit:
        dataset = dataset[:limit]
        logger.info(f"Limited to {limit} questions")

    results = []
    t0 = time.time()

    for i, item in enumerate(dataset):
        qid = item.get("id", f"q{i}")
        question = item["question"]
        expected_tools = item.get("expected_tools", [])
        expected_sources = item.get("expected_sources", [])
        criteria = item.get("criteria", [])

        logger.info(f"[{i+1}/{len(dataset)}] Evaluating: {qid}")

        try:
            single_result = run_single_evaluation(
                question=question,
                expected_tools=expected_tools,
                expected_sources=expected_sources,
                criteria=criteria,
                thread_id=f"eval_{qid}",
                tenant_id=tenant_id,
                user_id=user_id,
            )
            single_result["id"] = qid
            results.append(single_result)

            if verbose:
                eval_result = single_result["evaluation"]
                logger.info(
                    f"  Score: {eval_result['score']} | "
                    f"Retrieval: {eval_result['retrieval_score']} | "
                    f"Tool: {eval_result['tool_score']} | "
                    f"Quality: {eval_result['quality_score']} | "
                    f"Hallucination: {eval_result['hallucination_score']}"
                )
        except Exception as e:
            logger.error(f"  FAILED: {qid} - {e}")
            results.append({
                "id": qid,
                "question": question,
                "answer": "",
                "tools_used": [],
                "sources": [],
                "companies": [],
                "duration": 0,
                "evaluation": {
                    "score": 0.0,
                    "retrieval_score": 0.0,
                    "tool_score": 0.0,
                    "quality_score": 0.0,
                    "hallucination_score": 0.0,
                    "issues": [{"type": "error", "severity": "critical", "message": str(e)}],
                    "passed": False,
                },
            })

    total_duration = round(time.time() - t0, 3)
    batch_result = evaluate_batch([r["evaluation"] for r in results])

    report = {
        "dataset": dataset_name,
        "total_questions": len(results),
        "duration": total_duration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "passed": batch_result["passed"],
            "failed": batch_result["failed"],
            "average_score": batch_result["average_score"],
            "metric_averages": batch_result.get("metric_averages", {}),
        },
        "results": results,
    }

    return report


def save_report(report: Dict[str, Any], filename: str = None) -> Path:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"eval_report_{timestamp}.json"

    report_path = _REPORTS_DIR / filename
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Report saved: {report_path}")
    return report_path