"""Production response boundary regressions from the third real five-question run."""

import json
from types import SimpleNamespace

from agent.reasoning_models import Evidence, ReasoningResult
from core.answer_grounding import sanitize_answer


def evidence(company, content, period, chunk):
    return Evidence(content=content, source=f"{company}.pdf", company=company,
                    metadata={"quarter": period, "chunk_id": chunk})


def test_swapped_company_values_in_one_line_are_not_validated_by_union():
    rows = [evidence("Apple", "Apple Q1 FY2027 revenue was $100B.", "Q1_FY2027", "apple"),
            evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6B.", "Q1_FY2027", "nv")]
    result = sanitize_answer("Compare Apple and NVIDIA revenue.",
                             "Apple revenue was $81.6B; NVIDIA revenue was $100B.", rows)
    assert "$81.6B" not in result.answer
    assert "$100B" not in result.answer


def test_unrelated_citation_does_not_validate_a_correct_value():
    rows = [evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6B.", "Q1_FY2027", "actual"),
            evidence("NVIDIA", "NVIDIA Q2 FY2027 revenue guidance was $91B.", "Q2_FY2027", "guidance")]
    result = sanitize_answer("What was NVIDIA revenue?",
                             "NVIDIA Q1 FY2027 revenue was $81.6B [Evidence 2].", rows)
    assert "$81.6B" not in result.answer


def test_grounded_completion_keeps_q4_net_income_and_avoids_scientific_notation():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q4 2025 net income attributable to common stockholders (GAAP) was $840 million.",
        "Q4_2025",
        "tesla-q4-net-income",
    )
    result = finalize_grounded_answer(
        "What was Tesla Q4 2025 net income?",
        "Insufficient evidence to support this numeric claim.",
        [row],
    )

    assert "Tesla Q4 2025 net income: 840 million USD [Evidence 1]" in result.answer
    assert "E+" not in result.answer


def test_non_gaap_net_income_does_not_suppress_default_gaap_fact_completion():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 net income attributable to common stockholders (GAAP) was $1,172 million. "
        "Tesla Q2 2025 net income attributable to common stockholders (non-GAAP) was $1,393 million.",
        "Q2_2025",
        "tesla-q2-net-income-bases",
    )
    result = finalize_grounded_answer(
        "Summarize Tesla's Q2 2025 financial performance.",
        "Tesla Q2 2025 non-GAAP net income was $1,393 million [Evidence 1].",
        [row],
    )

    assert "Tesla Q2 2025 net income: 1.172 billion USD [Evidence 1]" in result.answer
    assert "Tesla Q2 2025 non-GAAP net income was $1,393 million" in result.answer
    assert result.grounded.unsupported_count == 0


def test_generic_margin_answer_preserves_gaap_and_non_gaap_values_in_both_languages():
    from core.answer_policy import finalize_grounded_answer

    evidence_rows = [
        evidence(
            "NVIDIA",
            "Comparative periods include Q1 FY2027 and Q4 FY2026. "
            "For the quarter, GAAP and non-GAAP gross margins were 74.9% and 75.0%, respectively.",
            "Q1_FY2027",
            "nvidia-q1-margin-pair",
        ),
    ]
    from core.fact_ledger import FactLedger

    margin_facts = [
        fact
        for fact in FactLedger.from_evidence(evidence_rows).facts
        if fact.metric_id == "gross_margin"
    ]
    assert {(fact.fact_period, str(fact.normalized_value)) for fact in margin_facts} == {
        ("Q1_FY2027", "74.9"),
        ("Q1_FY2027", "75.0"),
    }

    english = finalize_grounded_answer(
        "What does NVIDIA's Q1 FY2027 report say about margins?",
        "NVIDIA Q1 FY2027 gross margin was 74.9% [Evidence 1].",
        evidence_rows,
    )
    chinese = finalize_grounded_answer(
        "英伟达 2027 财年第一季度财报如何描述利润率？",
        "英伟达 Q1 FY2027 毛利率为 74.9% [Evidence 1]。",
        evidence_rows,
    )

    for result in (english, chinese):
        assert "74.9%" in result.answer
        assert "75%" in result.answer
        assert result.grounded.unsupported_count == 0
        basis_requirements = {
            item["accounting_basis"]: item
            for item in result.plan.as_dict(result.ledger, result.answer)["required"]
        }
        assert set(basis_requirements) == {"gaap", "non_gaap"}
        assert all(item["answer_present"] for item in basis_requirements.values())
    assert "GAAP gross margin" in english.answer
    assert "non-GAAP gross margin" in english.answer
    assert "GAAP毛利率" in chinese.answer
    assert "非GAAP毛利率" in chinese.answer


def test_summary_and_comparison_plans_keep_both_reported_margin_bases():
    from core.answer_policy import finalize_grounded_answer
    from core.fact_ledger import FactLedger
    from core.required_fact_plan import infer_required_fact_plan

    nvidia = evidence(
        "NVIDIA",
        "Comparative periods include Q1 FY2027 and Q4 FY2026. "
        "For the quarter, GAAP and non-GAAP gross margins were 74.9% and 75.0%, respectively.",
        "Q1_FY2027",
        "nvidia-q1-paired-margins",
    )
    summary_question = "Summarize NVIDIA's financial performance in Q1 FY2027."
    summary = finalize_grounded_answer(
        summary_question,
        "NVIDIA reported a strong financial quarter [Evidence 1].",
        [nvidia],
    )
    assert "GAAP gross margin: 74.9%" in summary.answer
    assert "non-GAAP gross margin: 75%" in summary.answer
    summary_margin_specs = [
        item
        for item in summary.plan.as_dict(summary.ledger, summary.answer)["required"]
        if item["metric_id"] == "gross_margin"
    ]
    assert {item["accounting_basis"] for item in summary_margin_specs} == {"gaap", "non_gaap"}

    tesla = evidence(
        "Tesla",
        "Tesla Q1 FY2027 gross margin was 17.0%.",
        "Q1_FY2027",
        "tesla-q1-gross-margin",
    )
    comparison = infer_required_fact_plan(
        "Compare Tesla and NVIDIA Q1 FY2027 gross margin.",
        [tesla, nvidia],
    )
    nvidia_comparison_bases = {
        status.spec.accounting_basis
        for status in comparison.statuses(FactLedger.from_evidence([tesla, nvidia]), "")
        if status.spec.company == "nvidia" and status.spec.metric_id == "gross_margin"
    }
    assert nvidia_comparison_bases == {"gaap", "non_gaap"}


def test_business_development_answer_drops_unrequested_financial_stats_but_keeps_operations():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 total revenue was $22,496 million and gross margin was 17.2%. "
        "Q2 2025 production was 410,244 vehicles and deliveries were 384,122. "
        "Tesla launched Robotaxi service in 2025.",
        "Q2_2025",
        "tesla-development-summary",
    )
    question = "Summarize Tesla's major business developments during Q2 2025."
    raw = (
        "Financial summary:\n"
        "- Q2 total revenue was $22,496 million [Evidence 1].\n"
        "- Gross margin was 17.2% [Evidence 1].\n\n"
        "Operational highlights:\n"
        "- Production was 410,244 vehicles and deliveries were 384,122 [Evidence 1].\n\n"
        "Business developments:\n"
        "- Tesla launched Robotaxi service in 2025 [Evidence 1]."
    )

    result = finalize_grounded_answer(question, raw, [row])

    assert "$22,496" not in result.answer
    assert "17.2%" not in result.answer
    assert "410,244" in result.answer
    assert "384,122" in result.answer
    assert "Robotaxi" in result.answer


def test_supported_table_amount_retains_scale_and_column():
    row = evidence("Tesla", "Q4-2024 Q1-2025 Q2-2025 Q3-2025 Q4-2025\n"
                   "Total revenues 25,707 19,335 22,496 28,095 24,901", "Q2_2025", "table")
    row.metadata["table_context"] = "($ in millions)"
    result = sanitize_answer("Tesla Q2 2025 revenue?",
                             "Tesla Q2 2025 revenue was $22.496 billion [Evidence 1].", [row])
    assert "$22.496 billion" in result.answer
    assert result.unsupported_count == 0


def test_third_company_and_wrong_metric_cannot_borrow_matching_numbers():
    rows = [evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6B.", "Q1_FY2027", "nv")]
    for answer in ("Microsoft revenue was $81.6B.", "NVIDIA net income was $81.6B."):
        result = sanitize_answer("What was NVIDIA revenue?", answer, rows)
        assert "$81.6B" not in result.answer


def test_every_derived_percentage_must_be_verified():
    rows = [evidence("NVIDIA", "Current revenue $120B; prior revenue $100B.", "", "nv")]
    result = sanitize_answer("NVIDIA revenue growth?", "Revenue grew 20% YoY and 99% QoQ.", rows)
    assert "99%" not in result.answer


def test_supported_uncited_fact_receives_its_actual_source():
    rows = [evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6B.", "Q1_FY2027", "nv")]
    result = sanitize_answer("NVIDIA revenue?", "NVIDIA revenue was $81.6B.", rows)
    assert "$81.6B" in result.answer
    assert "[Evidence 1]" in result.answer


def test_citations_stay_bound_to_their_clauses_on_second_pass():
    rows = [evidence("Apple", "Apple revenue was $100B.", "", "apple"),
            evidence("NVIDIA", "NVIDIA revenue was $81.6B.", "", "nv")]
    question = "Compare Apple and NVIDIA revenue."
    first = sanitize_answer(question, "Apple revenue was $100B; NVIDIA revenue was $81.6B.", rows)
    second = sanitize_answer(question, first.answer, rows)
    assert second.unsupported_count == 0
    assert second.answer == first.answer
    assert "$100B [Evidence 1];" in second.answer
    assert "$81.6B [Evidence 2]." in second.answer


def test_post_sentence_citation_cannot_be_borrowed_by_next_company():
    rows = [evidence("Apple", "Apple revenue was $100B.", "", "apple"),
            evidence("NVIDIA", "NVIDIA revenue was $81.6B.", "", "nv")]
    question = "Compare Apple and NVIDIA revenue."
    result = sanitize_answer(question,
                             "Apple revenue was $100B. [Evidence 2] NVIDIA revenue was $81.6B. [Evidence 2]",
                             rows)
    assert "$100B" not in result.answer
    assert "$81.6B [Evidence 2]." in result.answer


def test_completed_table_fact_uses_readable_period_when_metadata_is_unknown():
    from core.answer_policy import finalize_grounded_answer

    row = evidence("Tesla", "Q4-2024 Q1-2025 Q2-2025 Q3-2025 Q4-2025\n"
                   "Total revenues 25,707 19,335 22,496 28,095 24,901", "Unknown", "table")
    row.metadata["table_context"] = "($ in millions)"
    result = finalize_grounded_answer("Tesla Q2 2025 revenue?", "Insufficient evidence.", [row])
    assert "Tesla Q2 2025 revenue: 22.496 billion USD [Evidence 1]." in result.answer
    assert "25.707" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_data_center_revenue_heading_fact_replaces_wrong_consolidated_revenue_answer():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "NVIDIA",
        "Data Center\n\nFirst-quarter revenue was a record $75. 2 billion, "
        "up 21% from the previous quarter and up 92% from a year ago.",
        "Q1_FY2027",
        "dc-q1",
    )
    result = finalize_grounded_answer(
        "What does NVIDIA report about Data Center performance in Q1 FY2027?",
        "NVIDIA Q1 FY2027 revenue was $81.615 billion [Evidence 1].",
        [row],
    )

    assert "$81.615 billion" not in result.answer
    assert "Data Center" in result.answer
    assert "75.2 billion" in result.answer
    assert result.grounded.unsupported_count == 0


def test_growth_driver_question_recovers_cited_driver_text_not_only_the_metric():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "NVIDIA",
            "NVIDIA Q1 FY2027 Data Center revenue was $75.2 billion, up 92% year over year.",
            "Q1_FY2027",
            "nvidia-q1-dc-revenue",
        ),
        evidence(
            "NVIDIA",
            "The buildout of AI factories is accelerating at extraordinary speed. "
            "Agentic AI has arrived, generating real value and scaling rapidly across companies.",
            "Q1_FY2027",
            "nvidia-q1-drivers",
        ),
        evidence(
            "Apple",
            "Apple's growth drivers include services demand and higher App Store sales.",
            "Q1_FY2027",
            "apple-growth-drivers",
        ),
        evidence(
            "NVIDIA",
            "NVIDIA Q2 FY2027 advertising revenue grew due to increased demand.",
            "Q2_FY2027",
            "nvidia-q2-drivers",
        ),
        evidence(
            "NVIDIA",
            "Certain forward-looking statements are subject to risks and uncertainties about growth drivers.",
            "Q1_FY2027",
            "nvidia-safe-harbor",
        ),
        evidence(
            "NVIDIA",
            "NVIDIA Q2 FY2027 revenue guidance is $91.0 billion.",
            "Q1_FY2027",
            "nvidia-q2-guidance",
        ),
    ]
    raw = (
        "The available evidence does not identify the Data Center growth drivers. "
        "NVIDIA Q2 FY2027 revenue guidance was $91.0 billion [Evidence 3]."
    )

    english = finalize_grounded_answer(
        "Why did NVIDIA's Data Center business grow in Q1 FY2027?", raw, rows
    )
    chinese = finalize_grounded_answer(
        "英伟达的数据中心业务在 2027 财年第一季度为什么增长？", raw, rows
    )

    for result in (english, chinese):
        assert "AI factories" in result.answer
        assert "Agentic AI" in result.answer
        assert "91.0 billion" not in result.answer
        assert "App Store sales" not in result.answer
        assert "advertising revenue grew" not in result.answer
        assert "safe-harbor" not in result.answer.casefold()
        assert result.grounded.unsupported_count == 0
    assert "Related filing context" in english.answer
    assert "not an explicit attribution" in english.answer
    assert "财报相关背景" in chinese.answer
    assert "未明确归因" in chinese.answer
    assert "[Evidence 2]" in english.answer
    assert "[Evidence 2]" in chinese.answer


def test_broad_financial_summary_includes_reported_growth_driver_when_available():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "NVIDIA",
            "NVIDIA Q1 FY2027 revenue was $81.615 billion.",
            "Q1_FY2027",
            "nvidia-q1-revenue",
        ),
        evidence(
            "NVIDIA",
            "The buildout of AI factories—the largest infrastructure expansion in human history—is accelerating at extraordinary speed.",
            "Q1_FY2027",
            "nvidia-q1-driver",
        ),
    ]
    raw = "NVIDIA Q1 FY2027 revenue was $81.615 billion [Evidence 1]."

    english = finalize_grounded_answer(
        "Summarize NVIDIA's financial performance in Q1 FY2027.", raw, rows
    )
    chinese = finalize_grounded_answer(
        "总结英伟达 2027 财年第一季度的财务表现。", raw, rows
    )

    for result in (english, chinese):
        assert "AI factories" in result.answer
        assert "81.615 billion" in result.answer
        assert "[Evidence 2]" in result.answer
        assert result.grounded.unsupported_count == 0


def test_reported_yoy_and_qoq_growth_are_ledger_facts_and_complete_summary():
    from core.answer_policy import finalize_grounded_answer
    from core.fact_ledger import FactLedger

    row = evidence(
        "NVIDIA",
        "NVIDIA reported record revenue of $81.6 billion, up 20% from the previous quarter "
        "and up 85% from a year ago. Data Center revenue was a record $75.2 billion, "
        "up 92% from a year ago.",
        "Q1_FY2027",
        "nvidia-q1-growth",
    )
    ledger = FactLedger.from_evidence([row])

    assert [str(fact.normalized_value) for fact in ledger.lookup(
        company="NVIDIA", metric_id="revenue", period="Q1_FY2027", growth_basis="qoq"
    )] == ["20"]
    assert [str(fact.normalized_value) for fact in ledger.lookup(
        company="NVIDIA", metric_id="revenue", period="Q1_FY2027", growth_basis="yoy"
    )] == ["85"]
    assert [str(fact.normalized_value) for fact in ledger.lookup(
        company="NVIDIA", metric_id="data_center_revenue", period="Q1_FY2027", growth_basis="yoy"
    )] == ["92"]
    # Growth percentages must not pollute the base-revenue lookup.
    assert all(fact.unit != "percent" for fact in ledger.lookup(
        company="NVIDIA", metric_id="revenue", period="Q1_FY2027"
    ))

    result = finalize_grounded_answer(
        "Summarize NVIDIA's financial performance in Q1 FY2027.",
        "NVIDIA Q1 FY2027 revenue was $81.6 billion [Evidence 1].",
        [row],
    )
    assert "20%" in result.answer and "QoQ growth" in result.answer
    assert "85%" in result.answer and ("YoY" in result.answer or "year over year" in result.answer)
    assert "92%" in result.answer and "Data Center" in result.answer
    assert result.grounded.unsupported_count == 0


def test_reported_growth_comparison_basis_and_period_do_not_cross_bind():
    from core.answer_policy import finalize_grounded_answer
    from core.fact_ledger import FactLedger

    row = evidence(
        "NVIDIA",
        "NVIDIA Q2 FY2027 revenue guidance is $91.0 billion, up 11% from Q1 FY2027.",
        "Q2_FY2027",
        "nvidia-q2-guidance-growth",
    )
    ledger = FactLedger.from_evidence([row])
    assert ledger.lookup(
        company="NVIDIA", metric_id="revenue", period="Q1_FY2027", growth_basis="qoq"
    ) == ()

    result = finalize_grounded_answer(
        "Summarize NVIDIA's financial performance in Q1 FY2027.",
        "The retrieved passages are insufficient to answer this question reliably.",
        [row],
    )
    assert "11%" not in result.answer


def test_checked_in_nvidia_pdf_growth_rates_survive_the_complete_offline_policy():
    from pathlib import Path

    from core.answer_policy import finalize_grounded_answer
    from document_loader import load_pdf_chunks

    source = Path(__file__).resolve().parents[2] / "demo" / "documents" / "NVIDIA_sample.pdf"
    chunks = load_pdf_chunks(source, ocr_enabled=False)
    chunk = next(item for item in chunks if "up 20% from the previous quarter" in item.text)
    row = Evidence(
        content=chunk.text,
        source=source.name,
        company="NVIDIA",
        confidence=1.0,
        metadata={
            "quarter": "Q1_FY2027",
            "page": chunk.page,
            "content_type": chunk.content_type,
            "chunk_id": "nvidia-real-q1-release-growth",
        },
    )
    result = finalize_grounded_answer(
        "Summarize NVIDIA's financial performance in Q1 FY2027.",
        "NVIDIA Q1 FY2027 revenue was $81.6 billion [Evidence 1].",
        [row],
    )

    assert "revenue YoY growth: 85%" in result.answer
    assert "revenue QoQ growth: 20%" in result.answer
    assert "Data Center revenue YoY growth: 92%" in result.answer
    assert "91.0 billion" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_tesla_q2_summary_does_not_inherit_q4_yoy_from_trailing_table_column():
    from pathlib import Path

    from core.answer_policy import finalize_grounded_answer
    from document_loader import get_document_period, load_pdf_chunks

    source = Path(__file__).resolve().parents[2] / "demo" / "documents" / "Tesla_sample.pdf"
    chunks = load_pdf_chunks(source, ocr_enabled=False)
    document_period = get_document_period(chunks)
    chunk = next(
        item for item in chunks
        if "Metric: Total revenues" in str(item.text or "") and "YoY: -3%" in str(item.text or "")
    )
    row = Evidence(
        content=str(chunk.text or ""),
        source=source.name,
        company="Tesla",
        confidence=1.0,
        metadata={
            "quarter": document_period,
            "page": chunk.page,
            "section": chunk.section,
            "content_type": chunk.content_type,
            "table_context": str(getattr(chunk, "table_context", "") or ""),
            "chunk_id": "tesla-real-financial-summary-table",
        },
    )
    result = finalize_grounded_answer(
        "Summarize Tesla's financial performance in Q2 2025.",
        "Tesla Q2 2025 revenue was $22,496 million [Evidence 1].",
        [row],
    )

    assert "$22,496 million" in result.answer
    assert "-3%" not in result.answer
    assert "Q2 2025 revenue YoY growth" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_tesla_q2_cannot_borrow_q4_yoy_percentage_from_same_comparative_row():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content=(
            "Financial table row | Metric: Total revenues | Q4-2024: 25,707 | "
            "Q2-2025: 22,496 | Q4-2025: 24,901 | YoY: -3%"
        ),
        source="Tesla_sample.pdf",
        company="Tesla",
        confidence=1.0,
        metadata={
            "quarter": "Q4_2025",
            "content_type": "table",
            "table_context": "($ in millions) | Q4-2024 | Q2-2025 | Q4-2025 | YoY",
            "chunk_id": "tesla-comparative-revenue-row",
        },
    )

    result = finalize_grounded_answer(
        "What was Tesla's total revenue and YoY change in Q2 2025?",
        "Tesla Q2 2025 total revenue was $22,496 million, down 3% YoY [Evidence 1].",
        [row],
    )

    assert "22,496 million" in result.answer
    assert "3% YoY" not in result.answer
    assert result.grounded.unsupported_count > 0


def test_tesla_q2_yoy_cannot_be_derived_from_q4_2024_and_q2_2025_values():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content=(
            "Financial table row | Metric: Total revenues | Q4-2024: 25,707 | "
            "Q2-2025: 22,496 | Q4-2025: 24,901 | YoY: -3%"
        ),
        source="Tesla_sample.pdf",
        company="Tesla",
        confidence=1.0,
        metadata={
            "quarter": "Q4_2025",
            "content_type": "table",
            "table_context": "($ in millions) | Q4-2024 | Q2-2025 | Q4-2025 | YoY",
            "chunk_id": "tesla-comparative-revenue-row",
        },
    )

    result = finalize_grounded_answer(
        "What was Tesla's total revenue and YoY change in Q2 2025?",
        "Tesla Q2 2025 total revenue was $22,496 million, down about 12.5% YoY [Evidence 1].",
        [row],
    )

    assert "22,496 million" in result.answer
    assert "12.5% YoY" not in result.answer
    assert result.grounded.unsupported_count > 0


def test_tesla_q2_yoy_can_be_deterministically_derived_from_matching_period_operands():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "Tesla",
            "Financial table row | Metric: Total revenues | Q2-2025: 22,496",
            "Q2_2025",
            "tesla-q2-2025-revenue",
        ),
        evidence(
            "Tesla",
            "Financial table row | Metric: Total revenues | Q2-2024: 25,707",
            "Q2_2024",
            "tesla-q2-2024-revenue",
        ),
    ]

    result = finalize_grounded_answer(
        "What was Tesla's total revenue and YoY change in Q2 2025?",
        "Tesla Q2 2025 total revenue was $22,496 million, down 12.5% YoY [Evidence 1] [Evidence 2].",
        rows,
    )

    assert "22,496 million" in result.answer
    assert "12.5% YoY" in result.answer
    assert result.grounded.derivable_count == 1
    assert result.grounded.unsupported_count == 0


def test_bilingual_services_performance_summary_includes_period_matched_driver_context():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "Apple",
            "Apple Q2 FY2026 Services net sales were $30.976 billion.",
            "Q2_FY2026",
            "apple-q2-services-revenue",
        ),
        evidence(
            "Apple",
            "Services net sales increased during the second quarter of 2026 compared to Q2 2025 primarily due to higher net sales from advertising, the App Store, and cloud services.",
            "Q2_FY2026",
            "apple-q2-services-growth-drivers",
        ),
        evidence(
            "Apple",
            "Services revenue increased in Q3 FY2026 primarily due to higher advertising sales.",
            "Q3_FY2026",
            "apple-q3-services-growth-drivers",
        ),
        evidence(
            "NVIDIA",
            "NVIDIA Q2 FY2026 Services net sales increased due to App Store subscriptions.",
            "Q2_FY2026",
            "wrong-company-services-growth-drivers",
        ),
    ]
    cases = (
        (
            "How did Apple's Services business perform in Q2 2026?",
            "Apple Q2 FY2026 Services revenue was $30.976 billion [Evidence 1].",
        ),
        (
            "苹果的服务业务在 2026 年第二季度表现如何？",
            "苹果 Q2 FY2026 服务业务收入为 30.976 billion USD [Evidence 1]。",
        ),
    )

    for question, raw in cases:
        result = finalize_grounded_answer(question, raw, rows)
        assert "30.976" in result.answer
        assert "advertising" in result.answer.casefold()
        assert "App Store" in result.answer
        assert "cloud services" in result.answer.casefold()
        assert "Q3 FY2026" not in result.answer
        assert "NVIDIA" not in result.answer
        assert result.grounded.unsupported_count == 0


def test_reported_growth_driver_removes_contradictory_generic_refusal():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "NVIDIA",
        "NVIDIA Q1 FY2027 Data Center revenue increased due to stronger AI infrastructure demand.",
        "Q1_FY2027",
        "nvidia-q1-driver",
    )
    cases = (
        (
            "What were NVIDIA's growth drivers in Q1 FY2027?",
            "The retrieved passages are insufficient to establish this information.",
        ),
        (
            "What were NVIDIA's growth drivers in Q1 FY2027?",
            "The retrieved passages are insufficient to answer this question reliably.",
        ),
        (
            "英伟达 2027 财年第一季度增长的主要驱动因素是什么？",
            "当前检索到的证据不足以确认该信息。",
        ),
        (
            "英伟达 2027 财年第一季度增长的主要驱动因素是什么？",
            "当前检索到的证据不足以可靠回答该问题。",
        ),
        (
            "英伟达 2027 财年第一季度的增长驱动因素是什么？",
            "当前检索到的证据不足以确认该信息。",
        ),
    )
    for question, refusal in cases:
        result = finalize_grounded_answer(question, refusal, [row])
        assert "AI infrastructure demand" in result.answer
        assert "insufficient" not in result.answer.casefold()
        assert "证据不足" not in result.answer
        assert result.grounded.unsupported_count == 0


def test_false_segment_revenue_absence_is_removed_when_source_has_segment_fact():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "NVIDIA",
        "Data Center\n\nFirst-quarter revenue was a record $75. 2 billion, "
        "up 21% from the previous quarter and up 92% from a year ago.",
        "Q1_FY2027",
        "dc-q1",
    )
    result = finalize_grounded_answer(
        "Summarize the major business segments discussed in NVIDIA Q1 FY2027.",
        "Business segments:\nThe Evidence does not provide a business segment breakdown for NVIDIA Q1 FY2027.\n"
        "No segment-level revenue, operating income, or other segment metrics are reported.",
        [row],
    )

    assert "does not provide a business segment breakdown" not in result.answer
    assert "No segment-level revenue" not in result.answer
    assert "75.2 billion" in result.answer
    assert "data_center_revenue" in " ".join(result.added_fact_ids)


def test_segment_overview_keeps_segment_facts_without_appending_consolidated_metrics():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence("NVIDIA", "Data Center\n\nFirst-quarter revenue was a record $75.2 billion.", "Q1_FY2027", "dc"),
        evidence("NVIDIA", "NVIDIA Q1 FY2027 total revenue was $81.6 billion.", "Q1_FY2027", "total"),
        evidence("NVIDIA", "NVIDIA Q1 FY2027 net income was $18.8 billion.", "Q1_FY2027", "income"),
    ]
    result = finalize_grounded_answer(
        "Summarize the major business segments discussed in NVIDIA Q1 FY2027.",
        "Data Center is one of NVIDIA's major business segments [Evidence 1]. "
        "Consolidated revenue was $81.6 billion [Evidence 2]; "
        "net income was $18.8 billion [Evidence 3].",
        rows,
    )

    assert "75.2 billion" in result.answer
    assert "81.6 billion" not in result.answer
    assert "18.8 billion" not in result.answer
    assert [item.metric_id for item in result.plan.required] == ["data_center_revenue"]


def test_multi_company_risk_answer_drops_supported_but_unrequested_revenue_claims():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence("Apple", "Apple risk factors include new regulations and supply constraints.", "Q2_2026", "apple-risk"),
        evidence("Tesla", "Tesla risk factors include tariff exposure and production ramp delays.", "Q2_2025", "tesla-risk"),
        evidence("Apple", "Apple Q2 FY2026 total revenue was $94.8 billion.", "Q2_2026", "apple-revenue"),
        evidence("Tesla", "Tesla Q2 2025 total revenue was $22.5 billion.", "Q2_2025", "tesla-revenue"),
    ]
    result = finalize_grounded_answer(
        "Compare the main risks mentioned in Apple and Tesla reports.",
        "Apple's risks include regulatory changes and supply constraints [Evidence 1]. "
        "Tesla faces tariff exposure and production ramp risks [Evidence 2]. "
        "Apple revenue was $94.8 billion [Evidence 3]. "
        "Tesla revenue was $22.5 billion [Evidence 4].",
        rows,
    )

    assert "regulatory changes" in result.answer
    assert "tariff exposure" in result.answer
    assert "94.8 billion" not in result.answer
    assert "22.5 billion" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_chinese_multi_company_risk_answer_drops_unrequested_revenue_claims():
    from core.answer_policy import _scope_answer

    scoped, removed = _scope_answer(
        "比较 Apple 和 Tesla 报告披露的主要风险。",
        "Apple风险包括法规变化和供应限制 [Evidence 1]。\n"
        "Tesla风险包括关税暴露和生产爬坡延误 [Evidence 2]。\n"
        "Apple总收入为94.8 billion USD [Evidence 3]。\n"
        "Tesla总收入为22.5 billion USD [Evidence 4]。",
    )

    assert "法规变化" in scoped
    assert "关税暴露" in scoped
    assert "94.8 billion" not in scoped
    assert "22.5 billion" not in scoped
    assert len(removed) == 2


def test_risk_answer_keeps_supported_metric_when_same_claim_explains_risk_link():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 gross margin was 17.2% amid rising tariff exposure.",
        "Q2_2025",
        "tesla-margin-risk",
    )
    result = finalize_grounded_answer(
        "What financial risks are associated with Tesla?",
        "Tesla Q2 2025 gross margin was 17.2%, while tariff exposure remains a risk [Evidence 1].",
        [row],
    )

    assert "17.2%" in result.answer
    assert "tariff exposure" in result.answer
    assert result.grounded.unsupported_count == 0


def test_false_margin_absence_is_replaced_when_fact_ledger_has_the_value():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2-2025 gross margin was 17.2%.",
        "Q2_2025",
        "tesla-margin-q2",
    )
    result = finalize_grounded_answer(
        "What was Tesla's gross margin in Q2 2025?",
        "No specific gross margin percentage figures are provided.",
        [row],
    )

    assert "No specific gross margin" not in result.answer
    assert "17.2%" in result.answer
    assert result.plan.as_dict(result.ledger, result.answer)["required"][0]["answer_present"]


def test_generic_margin_absence_cannot_survive_a_supported_q1_fact_completion():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "NVIDIA",
        "NVIDIA reported results for Q1 FY2027. GAAP and non-GAAP gross margins were 74.9% and 75.0%.",
        "Q1_FY2027",
        "nvidia-q1-margins",
    )
    raw = (
        "Direct financial answer:\n\n"
        "The Evidence does not contain NVIDIA's reported (actual) margin figures for Q1 FY2027; "
        "that fact is missing. The required Q1 FY2027 margin fact is therefore not available in the Evidence.\n"
        "This is an outlook value for Q2 FY2027, not a reported Q1 FY2027 result."
    )
    english = finalize_grounded_answer(
        "What does NVIDIA's Q1 FY2027 report say about margins?", raw, [row]
    )
    chinese = finalize_grounded_answer(
        "英伟达 2027 财年第一季度财报如何描述利润率？", raw, [row]
    )

    for result in (english, chinese):
        assert "74.9%" in result.answer
        assert "does not contain NVIDIA's reported" not in result.answer
        assert "not available in the Evidence" not in result.answer
        assert "This is an outlook value for Q2 FY2027" not in result.answer
        assert result.grounded.unsupported_count == 0
    assert english.verified_facts_only_projection and chinese.verified_facts_only_projection
    assert "Direct financial answer" not in english.answer
    assert "直接财务回答" not in chinese.answer
    assert "Direct financial answer" not in chinese.answer
    english_required = english.plan.as_dict(english.ledger, english.answer)["required"]
    chinese_required = chinese.plan.as_dict(chinese.ledger, chinese.answer)["required"]
    assert [(item["company"], item["metric_id"], item["period"], item["answer_present"]) for item in english_required] == [
        ("nvidia", "gross_margin", "Q1_FY2027", True)
    ]
    assert [(item["company"], item["metric_id"], item["period"], item["answer_present"]) for item in chinese_required] == [
        ("nvidia", "gross_margin", "Q1_FY2027", True)
    ]


def test_english_question_does_not_return_chinese_provider_prose_after_wrong_period_removal():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "NVIDIA",
        "NVIDIA Q2 FY2027 outlook: revenue is expected to be $91 billion USD.",
        "Q2_FY2027",
        "nvidia-q2-guidance",
    )
    result = finalize_grounded_answer(
        "What drove the chip company's data-center business in its first fiscal quarter of 2027?",
        "Direct financial answer:\n"
        "- 证据未说明 NVIDIA 数据中心业务在第一财季 2027 的具体驱动因素。\n"
        "- NVIDIA Q2 FY2027 revenue: 91 billion USD [Evidence 1].",
        [row],
    )

    assert "91 billion" not in result.answer
    assert "具体驱动因素" not in result.answer
    assert "insufficient" in result.answer.casefold()
    assert result.grounded.unsupported_count == 0


def test_analysis_of_data_center_business_uses_q1_fact_and_rejects_q2_guidance():
    from core.answer_policy import finalize_grounded_answer

    q1 = evidence(
        "NVIDIA",
        "NVIDIA Q1 FY2027 Data Center revenue was $75.2 billion, up 92% year over year.",
        "Q1_FY2027",
        "nvidia-q1-data-center",
    )
    q2 = evidence(
        "NVIDIA",
        "NVIDIA Q2 FY2027 outlook: revenue is expected to be $91 billion USD.",
        "Q2_FY2027",
        "nvidia-q2-guidance",
    )
    question = "What drove the chip company's data-center business in its first fiscal quarter of 2027?"
    result = finalize_grounded_answer(
        question,
        "The available evidence does not establish the requested driver.\n"
        "NVIDIA Q2 FY2027 revenue was $91 billion USD [Evidence 2].",
        [q1, q2],
    )

    assert "91 billion" not in result.answer
    assert "75.2 billion" in result.answer
    assert "data_center_revenue" in " ".join(result.added_fact_ids)
    assert result.grounded.unsupported_count == 0


def test_english_and_chinese_numeric_fallback_share_fact_and_citation():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content="NVIDIA Q1 FY2027 revenue was $81.6 billion.",
        source="NVIDIA_Q1_FY2027.pdf",
        company="NVIDIA",
        metadata={"chunk_id": "nvidia-q1-revenue", "quarter": "Q1_FY2027", "page": 1},
    )
    english = finalize_grounded_answer(
        "What was NVIDIA Q1 FY2027 revenue?",
        "Insufficient evidence to support this numeric claim.",
        [row],
    )
    chinese = finalize_grounded_answer(
        "英伟达 2027 财年第一季度营收是多少？",
        "证据不足，无法可靠支持该数字结论。",
        [row],
    )

    assert "81.6 billion" in english.answer
    assert "81.6 billion" in chinese.answer
    assert "英伟达 Q1 FY2027 营收" in chinese.answer
    assert [fact.normalized_value for fact in english.ledger.lookup(metric_id="revenue")] == [
        fact.normalized_value for fact in chinese.ledger.lookup(metric_id="revenue")
    ] == [81_600_000_000]
    assert [item.metadata["chunk_id"] for item in english.grounded.evidence] == [
        item.metadata["chunk_id"] for item in chinese.grounded.evidence
    ] == ["nvidia-q1-revenue"]


def test_english_and_chinese_service_business_queries_share_the_same_required_fact():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Apple",
        "Apple Q2 FY2026 Services net sales were $30,976 million.",
        "Q2_2026",
        "apple-services-q2",
    )
    english = finalize_grounded_answer(
        "How did Apple's Services business perform in Q2 2026?",
        "Insufficient evidence to support this numeric claim.",
        [row],
    )
    chinese = finalize_grounded_answer(
        "苹果的服务业务在 2026 年第二季度表现如何？",
        "证据不足，无法可靠支持该数字结论。",
        [row],
    )

    en_required = english.plan.as_dict(english.ledger, english.answer)["required"]
    zh_required = chinese.plan.as_dict(chinese.ledger, chinese.answer)["required"]
    assert [(item["metric_id"], item["period"], item["answer_present"]) for item in en_required] == [
        ("services_revenue", "Q2_2026", True)
    ]
    assert [(item["metric_id"], item["period"], item["answer_present"]) for item in zh_required] == [
        ("services_revenue", "Q2_2026", True)
    ]
    assert "30.976 billion" in english.answer
    assert "30.976 billion" in chinese.answer


def test_services_and_other_revenue_answer_is_not_duplicated_by_fact_completion():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Apple",
        "Apple Q2 FY2026 Services and other revenue was $30,976 million.",
        "Q2_2026",
        "apple-services-and-other-q2",
    )
    answer = "Apple Q2 FY2026 Services and other revenue was $30,976 million."

    result = finalize_grounded_answer(
        "How did Apple's Services business perform in Q2 2026?", answer, [row]
    )

    assert result.answer.casefold().count("services and other revenue") == 1
    assert "Services revenue:" not in result.answer
    required = result.plan.as_dict(result.ledger, result.answer)["required"]
    assert [(item["metric_id"], item["answer_present"]) for item in required] == [
        ("services_revenue", True)
    ]


def test_services_revenue_does_not_satisfy_consolidated_revenue_fact():
    from core.fact_ledger import FactLedger
    from core.required_fact_plan import RequiredFactSpec, answer_contains_fact

    rows = [
        evidence(
            "Apple",
            "Apple Q2 FY2026 Services and other revenue was $30,976 million.",
            "Q2_2026",
            "apple-services-and-other-q2",
        ),
        evidence(
            "Apple",
            "Apple Q2 FY2026 total revenue was $94,836 million.",
            "Q2_2026",
            "apple-total-revenue-q2",
        ),
    ]
    ledger = FactLedger.from_evidence(rows)

    assert not answer_contains_fact(
        "Apple Q2 FY2026 Services and other revenue was $94,836 million.",
        RequiredFactSpec("Apple", "revenue", "Q2_2026", "headline revenue"),
        ledger,
    )
    assert answer_contains_fact(
        "Apple Q2 FY2026 total revenue was $94,836 million.",
        RequiredFactSpec("Apple", "revenue", "Q2_2026", "headline revenue"),
        ledger,
    )


def test_unqualified_bilingual_data_center_summary_inherits_same_filing_period():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "NVIDIA",
            "NVIDIA Q1 FY2027 total revenue was $81.6 billion.",
            "Q1_FY2027",
            "nvidia-revenue-q1",
        ),
        evidence(
            "NVIDIA",
            "NVIDIA Q1 FY2027 gross margin was 74.9%.",
            "Q1_FY2027",
            "nvidia-margin-q1",
        ),
        evidence(
            "NVIDIA",
            "NVIDIA Q1 FY2027 Data Center revenue was $75.2 billion.",
            "Q1_FY2027",
            "nvidia-dc-q1",
        ),
    ]
    english = finalize_grounded_answer(
        "Tell me about NVDA's data centre performance.",
        "Insufficient evidence to support this numeric claim.",
        rows,
    )
    chinese = finalize_grounded_answer(
        "NVDA 的数据中心业务表现咋样？",
        "证据不足，无法可靠支持该数字结论。",
        rows,
    )

    en_required = english.plan.as_dict(english.ledger, english.answer)["required"]
    zh_required = chinese.plan.as_dict(chinese.ledger, chinese.answer)["required"]
    assert [(item["metric_id"], item["period"], item["answer_present"]) for item in en_required] == [
        ("data_center_revenue", "Q1_FY2027", True)
    ]
    assert [(item["metric_id"], item["period"], item["answer_present"]) for item in zh_required] == [
        ("data_center_revenue", "Q1_FY2027", True)
    ]
    assert "75.2 billion" in english.answer
    assert "75.2 billion" in chinese.answer
    assert "81.6 billion" not in english.answer and "74.9%" not in english.answer
    assert "81.6 billion" not in chinese.answer and "74.9%" not in chinese.answer


def test_bilingual_margin_followup_preserves_company_period_and_metric_scope():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 total gross margin was 17.2%; operating margin was 4.1%.",
        "Q2_2025",
        "tesla-q2-margins",
    )
    english = finalize_grounded_answer(
        "Tell me about Tesla's Q2 2025 performance.\nWhat did it say about margins?",
        "Insufficient evidence to support this numeric claim.",
        [row],
    )
    chinese = finalize_grounded_answer(
        "介绍一下特斯拉 2025 年第二季度的表现。\n那它的利润率表现呢？",
        "证据不足，无法可靠支持该数字结论。",
        [row],
    )

    def required_signature(result):
        return [
            (item["company"], item["metric_id"], item["period"], item["available"], item["answer_present"])
            for item in result.plan.as_dict(result.ledger, result.answer)["required"]
        ]

    expected = [
        ("tesla", "gross_margin", "Q2_2025", True, True),
        ("tesla", "operating_margin", "Q2_2025", True, True),
    ]
    assert required_signature(english) == expected
    assert required_signature(chinese) == expected
    assert "17.2%" in english.answer and "4.1%" in english.answer
    assert "17.2%" in chinese.answer and "4.1%" in chinese.answer


def test_chinese_question_cannot_leak_an_english_provider_answer():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content="NVIDIA Q1 FY2027 revenue was $81.6 billion.",
        source="NVIDIA_Q1_FY2027.pdf",
        company="NVIDIA",
        metadata={"chunk_id": "nvidia-q1-revenue", "quarter": "Q1_FY2027", "page": 1},
    )
    result = finalize_grounded_answer(
        "英伟达 2027 财年第一季度营收是多少？",
        "NVIDIA Q1 FY2027 revenue was $81.6 billion [Evidence 1].",
        [row],
    )

    assert "英伟达" in result.answer
    assert "营收" in result.answer
    assert "81.6 billion USD" in result.answer
    assert result.answer.count("[Evidence 1]") == 1
    assert result.grounded.unsupported_count == 0


def test_chinese_no_evidence_response_is_localized_without_provider_retry():
    from core.answer_policy import finalize_grounded_answer

    result = finalize_grounded_answer(
        "根据上传文件，阿里巴巴最新季度营收是多少？",
        "No relevant evidence found in uploaded documents.",
        [],
    )

    assert "证据不足" in result.answer
    assert "No relevant evidence" not in result.answer
    assert result.grounded.evidence == []


def test_english_question_cannot_leak_a_chinese_provider_answer():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content="NVIDIA Q1 FY2027 revenue was $81.6 billion.",
        source="NVIDIA_Q1_FY2027.pdf",
        company="NVIDIA",
        metadata={"chunk_id": "nvidia-q1-revenue", "quarter": "Q1_FY2027", "page": 1},
    )
    result = finalize_grounded_answer(
        "What was NVIDIA Q1 FY2027 revenue?",
        "英伟达 2027 财年第一季度营收为 81.6 billion USD [Evidence 1]。",
        [row],
    )

    assert "NVIDIA" in result.answer
    assert "revenue" in result.answer
    assert "81.6 billion USD" in result.answer
    assert "营收" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_bilingual_metric_projection_rejects_swapped_values_and_keeps_the_same_facts():
    from core.answer_policy import finalize_grounded_answer

    row = Evidence(
        content=(
            "NVIDIA Q1 FY2027 total revenue was $81.6 billion. "
            "Net income was $58.3 billion."
        ),
        source="NVIDIA_Q1_FY2027.pdf",
        company="NVIDIA",
        metadata={"chunk_id": "nvidia-q1-metrics", "quarter": "Q1_FY2027", "page": 1},
    )
    english = finalize_grounded_answer(
        "Summarize NVIDIA Q1 FY2027 revenue and net income.",
        "NVIDIA revenue was $58.3 billion and net income was $81.6 billion [Evidence 1].",
        [row],
    )
    chinese = finalize_grounded_answer(
        "总结英伟达 2027 财年第一季度营收和净利润。",
        "英伟达营收为 58.3 billion USD，净利润为 81.6 billion USD [Evidence 1]。",
        [row],
    )

    expected = {("revenue", "81600000000.0"), ("net_income", "58300000000.0")}
    english_facts = {(fact.metric_id, str(fact.normalized_value)) for fact in english.ledger.facts}
    chinese_facts = {(fact.metric_id, str(fact.normalized_value)) for fact in chinese.ledger.facts}
    assert expected <= english_facts & chinese_facts
    assert "$58.3 billion" not in english.answer and "$81.6 billion" not in english.answer
    assert "revenue: 81.6 billion USD" in english.answer
    assert "net income: 58.3 billion USD" in english.answer
    assert "英伟达 Q1 FY2027 营收: 81.6 billion USD" in chinese.answer
    assert "英伟达 Q1 FY2027 净利润: 58.3 billion USD" in chinese.answer
    assert "[Evidence 1]" in english.answer and "[Evidence 1]" in chinese.answer
    assert english.grounded.unsupported_count == chinese.grounded.unsupported_count == 0


def test_unscoped_fact_question_does_not_autocomplete_an_unrequested_revenue_metric():
    from core.answer_policy import finalize_grounded_answer

    row = evidence("Tesla", "Tesla Q2 2025 revenue was $22.496 billion.", "Q2_2025", "tesla-revenue")
    question = "How many employees did Tesla hire in Q2 2025?"
    result = finalize_grounded_answer(
        question,
        "Tesla does not publicly disclose gross hires for the quarter.",
        [row],
    )

    assert result.plan.required == ()
    assert "hires" in result.answer
    assert "22.496 billion" not in result.answer


def test_repeated_refusal_placeholders_are_removed_when_fact_is_available():
    from core.answer_policy import finalize_grounded_answer

    row = evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6 billion.", "Q1_FY2027", "nv")
    result = finalize_grounded_answer(
        "What was NVIDIA revenue in Q1 FY2027?",
        "Insufficient evidence to support this numeric claim.\n\n"
        "Insufficient evidence to support this numeric claim.",
        [row],
    )
    assert result.answer.count("Insufficient evidence") == 0
    assert "81.6 billion" in result.answer


def test_fiscal_marker_variant_keeps_split_period_fact_available_to_finalizer():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Apple",
        "Apple total net sales were $111,184 million.",
        "Q2_2026",
        "apple-total-net-sales-q2",
    )
    result = finalize_grounded_answer(
        "What were Apple's total net sales in Q2 FY2026?",
        "The evidence does not contain Apple's revenue.",
        [row],
    )

    assert "111.184 billion" in result.answer
    assert "does not contain" not in result.answer
    assert "[Evidence 1]" in result.answer
    assert result.grounded.unsupported_count == 0


def test_fiscal_marker_variant_keeps_narrative_fact_available_to_finalizer():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Apple",
        "Apple Q2 2026 Services net sales were $30,976 million.",
        "Q2_2026",
        "apple-services-narrative-q2",
    )
    result = finalize_grounded_answer(
        "How did Apple's Services business perform in Q2 FY2026?",
        "The evidence does not identify Apple's Services revenue.",
        [row],
    )

    assert "30.976 billion" in result.answer
    assert "does not identify" not in result.answer
    assert result.grounded.unsupported_count == 0


def test_fiscal_marker_variant_does_not_allow_different_metadata_quarter():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Apple",
        "Apple total net sales were $111,184 million.",
        "Q1_2026",
        "apple-total-net-sales-q1",
    )
    result = finalize_grounded_answer(
        "What were Apple's total net sales in Q2 FY2026?",
        "The evidence does not contain Apple's revenue.",
        [row],
    )

    assert "111.184 billion" not in result.answer
    assert "does not contain" not in result.answer
    assert "retrieved passages" in result.answer
    assert "[Evidence" not in result.answer


def test_partial_retrieval_cannot_turn_an_unrelated_citation_into_a_global_absence_claim():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "Apple",
            "Apple Q2 FY2026 report describes App Store regulatory investigations and legal proceedings.",
            "Q2_2026",
            "apple-regulatory-risk",
        )
    ]
    english = finalize_grounded_answer(
        "What was Apple's Services revenue in Q2 FY2026?",
        "Evidence limitation: Apple's Services business financial results are absent "
        "from the Evidence, so the question cannot be answered [Evidence 1].",
        rows,
    )
    chinese = finalize_grounded_answer(
        "苹果 2026 财年第二季度服务业务收入是多少？",
        "现有证据未能找到苹果 Services 业务的财务结果 [Evidence 1]。",
        rows,
    )

    assert "filing does not contain" not in english.answer.casefold()
    assert "retrieved passages" in english.answer.casefold()
    assert "未能找到" not in chinese.answer
    assert "检索到的证据" in chinese.answer
    assert "[Evidence" not in english.answer
    assert "[Evidence" not in chinese.answer


def test_comma_enumerated_metric_absence_claims_are_rewritten_bilingually():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence(
            "Apple",
            "Apple Q2 FY2026 report describes App Store regulatory investigations.",
            "Q2_2026",
            "apple-regulatory-risk",
        )
    ]
    english = finalize_grounded_answer(
        "Compare Apple and Tesla's financial performance.",
        "No Apple cost of revenues, gross profit, operating income, net income, "
        "or margin figures appear in the retrieved evidence [Evidence 1].",
        rows,
    )
    chinese = finalize_grounded_answer(
        "比较苹果和特斯拉的财务表现。",
        "当前检索到的证据中没有出现苹果的成本、毛利、营业利润、净利润或利润率数据 [Evidence 1]。",
        rows,
    )

    for result in (english, chinese):
        assert result.removed_lines
        assert "Apple cost of revenues" not in result.answer
        assert "没有出现苹果" not in result.answer
        assert "[Evidence 1]" not in result.answer
    assert "retrieved passages" in english.answer.casefold()
    assert "检索到的证据" in chinese.answer


def test_refusal_is_retained_when_no_fact_is_available():
    from core.answer_policy import finalize_grounded_answer

    row = evidence("NVIDIA", "NVIDIA discussed product launches.", "Q1_FY2027", "nv")
    result = finalize_grounded_answer(
        "What was NVIDIA revenue in Q1 FY2027?",
        "Insufficient evidence to support this numeric claim.",
        [row],
    )
    assert "Insufficient evidence" in result.answer


def test_unrelated_filing_numbers_do_not_erase_unsupported_financial_refusals():
    from core.answer_policy import finalize_grounded_answer

    revenue = evidence("Tesla", "Tesla Q2 2025 revenue was $22.496 billion.", "Q2_2025", "tesla-revenue")
    cases = (
        (
            "What is Tesla's stock price target for the next 12 months?",
            "Tesla could reach $500 with 40% upside over the next 12 months.",
            "The available filing evidence does not establish the requested metric: price target.",
        ),
        (
            "What was Tesla's China market share in 2025?",
            "Tesla held 12.5% market share after selling 500,000 vehicles.",
            "The available filing evidence does not establish the requested metric: market share.",
        ),
        (
            "How many gross hires did Tesla make?",
            "Tesla hired 10,000 employees.",
            "The available filing evidence does not establish the requested metric: hires.",
        ),
        (
            "特斯拉未来12个月股价目标是多少？",
            "特斯拉未来12个月目标价为500美元，上涨空间40%。",
            "现有财报证据未能证明所询股价目标，无法可靠作答。",
        ),
    )
    for question, raw_answer, expected_refusal in cases:
        result = finalize_grounded_answer(question, raw_answer, [revenue])
        assert result.answer == expected_refusal
        assert "$500" not in result.answer and "40%" not in result.answer
        assert "12.5%" not in result.answer and "10,000" not in result.answer


def test_unstructured_financial_request_can_use_explicitly_matching_cited_evidence():
    from core.answer_policy import finalize_grounded_answer

    target = evidence(
        "Tesla",
        "Tesla 12-month price target is $250 per share.",
        "Q2_2025",
        "tesla-price-target",
    )
    result = finalize_grounded_answer(
        "What is Tesla's stock price target for the next 12 months?",
        "Tesla's 12-month price target is $250 per share [Evidence 1].",
        [target],
    )
    assert "$250" in result.answer
    assert "price target" in result.answer.lower()
    assert "does not establish" not in result.answer


def test_supported_direct_fact_answer_uses_only_requested_ledger_fact():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 total revenues were $22.496 billion. Q2 operating margin was 4.1%.",
        "Q2_2025",
        "tesla-q2-financials",
    )
    result = finalize_grounded_answer(
        "What does Tesla report about revenue in Q2 2025?",
        "Tesla's automotive revenue was $16.661 billion and its operating margin was 4.1%. "
        "The company also faced weakening demand [Evidence 1].",
        [row],
    )

    assert result.verified_facts_only_projection
    assert "22.496 billion" in result.answer
    assert "revenue" in result.answer.casefold()
    assert "operating margin" not in result.answer.casefold()
    assert "weakening demand" not in result.answer.casefold()
    assert "[Evidence 1]" in result.answer
    assert result.removed_lines


def test_fact_only_projection_does_not_run_when_requested_fact_is_missing():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 discussed vehicle launches and energy storage deployments.",
        "Q2_2025",
        "tesla-narrative",
    )
    result = finalize_grounded_answer(
        "What was Tesla revenue in Q2 2025?",
        "Tesla revenue was $22.496 billion [Evidence 1].",
        [row],
    )

    assert not result.verified_facts_only_projection
    assert "22.496 billion" not in result.answer


def test_numeric_comparison_projects_each_company_from_its_own_ledger_partition():
    from core.answer_policy import finalize_grounded_answer

    rows = [
        evidence("Tesla", "Tesla Q2 2025 total revenue was $22.496 billion.", "Q2_2025", "tesla-revenue"),
        evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.615 billion.", "Q1_FY2027", "nvidia-revenue"),
    ]
    result = finalize_grounded_answer(
        "Compare Tesla and NVIDIA revenue.",
        "Tesla revenue was $81.615 billion and NVIDIA revenue was $22.496 billion. "
        "NVIDIA is therefore a much larger business [Evidence 1] [Evidence 2].",
        rows,
    )

    assert result.verified_facts_only_projection
    assert "Tesla Q2 2025 revenue: 22.496 billion USD" in result.answer
    assert "NVIDIA Q1 FY2027 revenue: 81.615 billion USD" in result.answer
    assert "Tesla revenue was $81.615" not in result.answer
    assert "NVIDIA revenue was $22.496" not in result.answer
    assert "larger business" not in result.answer


def test_causal_business_question_is_not_replaced_by_a_revenue_fact():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 automotive revenue was $16.661 billion. Lower vehicle pricing "
        "and a different product mix affected automotive revenue.",
        "Q2_2025",
        "tesla-automotive-drivers",
    )
    result = finalize_grounded_answer(
        "What factors affected Tesla's automotive business in Q2 2025?",
        "Lower vehicle pricing and a different product mix affected Tesla's automotive "
        "revenue [Evidence 1].",
        [row],
    )

    assert not result.verified_facts_only_projection
    assert "pricing" in result.answer.casefold()
    assert "product mix" in result.answer.casefold()


def test_no_trusted_retrieval_fails_closed_for_qualitative_and_numeric_drafts():
    from core.answer_policy import finalize_grounded_answer

    wrong_company = evidence(
        "NVIDIA",
        "NVIDIA Q1 FY2027 revenue was $81.615 billion and data-center demand was strong.",
        "Q1_FY2027",
        "nvidia-context",
    )
    result = finalize_grounded_answer(
        "What does Microsoft Azure report about revenue?",
        "Azure revenue was $81.615 billion and grew because of exceptional demand.",
        [wrong_company],
    )

    assert "retrieved passages" in result.answer.casefold()
    assert "81.615" not in result.answer
    assert "exceptional demand" not in result.answer
    assert not result.grounded.evidence


def test_empty_retrieval_cannot_return_provider_generated_narrative():
    from core.answer_policy import finalize_grounded_answer

    result = finalize_grounded_answer(
        "What risks did Tesla report in Q2 2025?",
        "Tesla faced intense competition and weakening demand in China.",
        [],
    )

    assert "No relevant uploaded-filing evidence" in result.answer
    assert "intense competition" not in result.answer
    assert "weakening demand" not in result.answer


def test_repeated_retrieval_limitations_are_compacted_to_one_without_supported_facts():
    from core.answer_policy import finalize_grounded_answer

    source = evidence(
        "NVIDIA",
        "NVIDIA Q1 FY2027 risk factors include supply-chain and regulatory risks.",
        "Q1_FY2027",
        "nvidia-risk",
    )
    cases = (
        (
            "What risks are disclosed in NVIDIA Q1 FY2027?",
            "The retrieved passages are insufficient to establish this information.",
        ),
        (
            "NVIDIA Q1 FY2027 披露了哪些风险？",
            "当前检索到的证据不足以确认该信息。",
        ),
    )
    for question, refusal in cases:
        result = finalize_grounded_answer(
            question,
            " ".join([refusal] * 5),
            [source],
        )

        assert result.answer.count(refusal) == 1


def test_uncited_qualitative_claim_needs_its_own_relevant_source_clause():
    from core.answer_policy import finalize_grounded_answer

    row = evidence(
        "Tesla",
        "Tesla Q2 2025 risk factors include regulatory changes and adverse foreign exchange movements.",
        "Q2_2025",
        "tesla-q2-risk",
    )
    result = finalize_grounded_answer(
        "What risks did Tesla report in Q2 2025?",
        "Tesla disclosed regulatory and foreign-exchange risks. Consumer demand collapsed in China.",
        [row],
    )

    assert "regulatory and foreign-exchange risks" in result.answer
    assert "[Evidence 1]" in result.answer
    assert "Consumer demand collapsed" not in result.answer


def test_metric_keyword_and_number_from_different_source_rows_do_not_support_each_other():
    from core.answer_policy import finalize_grounded_answer

    mixed = evidence(
        "Tesla",
        "Tesla market share was not disclosed.\nQ2 revenue growth was 12.5%.",
        "Q2_2025",
        "mixed-metrics",
    )
    result = finalize_grounded_answer(
        "What was Tesla market share in Q2 2025?",
        "Tesla market share was 12.5% [Evidence 1].",
        [mixed],
    )
    assert result.answer == (
        "The available filing evidence does not establish the requested metric: market share."
    )
    assert "12.5%" not in result.answer


def test_production_response_is_finally_grounded_and_audit_preserves_raw(monkeypatch, tmp_path):
    from core import core_engine
    rows = [evidence("Tesla", "Q4-2024 Q1-2025 Q2-2025 Q3-2025 Q4-2025\n"
                     "Total revenues 25,707 19,335 22,496 28,095 24,901", "Q2_2025", "tesla-table"),
            evidence("NVIDIA", "NVIDIA Q1 FY2027 revenue was $81.6 billion.", "Q1_FY2027", "nv")]
    rows[0].metadata["table_context"] = "($ in millions)"
    raw = "# Business Strategy\nNVIDIA is investing in AI.\n# Revenue\nInsufficient evidence."
    runtime_result = SimpleNamespace(
        execution={}, workflow={"type": "rag"}, evidence=rows, citations=[], context="",
        provider_instance=None, planning={}, plan=None, routing={}, intent_result={},
        reasoning_result=ReasoningResult(facts=["Tesla revenue $25.707B. Uncited raw table 19,335 24,901"]),
    )
    monkeypatch.setattr(core_engine, "_get_request_runtime", lambda _: SimpleNamespace(run=lambda *a, **kw: runtime_result))
    monkeypatch.setattr(core_engine, "call_llm", lambda *a, **kw: raw)
    monkeypatch.setattr(core_engine, "DEBUG_MODE", False)
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("P1_3_SMOKE_AUDIT_PATH", str(audit))
    result = core_engine.run_rag("Compare Tesla and NVIDIA revenue performance.")
    assert "25,707" not in result.report
    assert "$25.707B" not in result.report
    assert "Business Strategy" not in result.report
    assert "22.496 billion" in result.report
    assert "81.6 billion" in result.report
    captured = json.loads(audit.read_text(encoding="utf-8"))
    assert captured["raw_llm_answer"] == raw
    assert captured["final_api_report"] == result.report
    final = captured["final_sanitized_answer"]
    assert "22.496 billion" in final and "81.6 billion" in final
    assert sanitize_answer("Compare Tesla and NVIDIA revenue performance.", final, result.evidence).unsupported_count == 0
    assert captured["final_evidence"][0]["content"]
    assert captured["final_evidence"][0]["metadata"]["chunk_id"]
