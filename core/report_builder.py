from agent.reasoning_models import ReasoningResult


def build_research_report(
    question,
    answer,
    citations,
    evidence_stats,
    reasoning_result: ReasoningResult = None,
):
    coverage_text = ""

    for source, count in evidence_stats.items():
        coverage_text += f"- {source}: {count} chunks\n"

    report = f"""
# Research Report

## Question
{question}

## Answer
{answer}
"""

    if reasoning_result and reasoning_result.facts:
        report += """
## Key Facts
"""
        for f in reasoning_result.facts:
            report += f"- {f}\n"

    if reasoning_result and reasoning_result.risks:
        report += """
## Risk Signals
"""
        for r in reasoning_result.risks:
            report += f"- {r}\n"

    if reasoning_result and reasoning_result.opportunities:
        report += """
## Opportunity Signals
"""
        for o in reasoning_result.opportunities:
            report += f"- {o}\n"

    if reasoning_result and reasoning_result.conclusion:
        report += f"""
## AI Conclusion

{reasoning_result.conclusion}
"""

    report += f"""
## Source Coverage
{coverage_text}
"""
    return report
