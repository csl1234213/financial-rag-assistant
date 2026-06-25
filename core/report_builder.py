def build_research_report(
    question,
    answer,
    citations,
    evidence_stats
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

    ## Source Coverage
    {coverage_text}
    """
    return report
