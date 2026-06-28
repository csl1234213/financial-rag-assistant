import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from prompt_builder import PROMPT_RULES, build_compare_prompt, build_prompt


@pytest.mark.unit
class TestBuildPrompt:
    def test_prompt_contains_question(self):
        prompt = build_prompt(
            question="What is Apple's revenue?",
            context="Apple revenue was $383B in 2023.",
        )
        assert "What is Apple's revenue?" in prompt

    def test_prompt_contains_context(self):
        prompt = build_prompt(
            question="What is Apple's revenue?",
            context="Apple revenue was $383B in 2023.",
        )
        assert "Apple revenue was $383B in 2023" in prompt

    def test_prompt_contains_prompt_rules(self):
        prompt = build_prompt(
            question="What is Apple's revenue?",
            context="Apple revenue was $383B in 2023.",
        )
        assert "professional financial analyst" in prompt

    def test_prompt_has_evidence_section(self):
        prompt = build_prompt(
            question="test",
            context="some context",
        )
        assert "EVIDENCE" in prompt

    def test_prompt_has_question_section(self):
        prompt = build_prompt(
            question="test",
            context="some context",
        )
        assert "QUESTION" in prompt

    def test_prompt_has_response_format(self):
        prompt = build_prompt(
            question="test",
            context="some context",
        )
        assert "RESPONSE FORMAT" in prompt

    def test_prompt_has_evidence_citation_instruction(self):
        prompt = build_prompt(
            question="test",
            context="some context",
        )
        assert "[Evidence 1]" in prompt

    def test_prompt_no_history_section_empty(self):
        prompt = build_prompt(
            question="test",
            context="some context",
        )
        assert "CONVERSATION HISTORY" in prompt

    def test_prompt_with_history(self):
        prompt = build_prompt(
            question="What about Tesla?",
            context="Tesla delivered 1.8M vehicles.",
            history=[
                {"q": "What is Apple's revenue?", "a": "$383B"},
                {"q": "What about profit?", "a": "$97B net income"},
            ],
        )
        assert "What is Apple's revenue?" in prompt
        assert "$383B" in prompt
        assert "What about profit?" in prompt
        assert "$97B net income" in prompt

    def test_prompt_history_truncated_to_last_3(self):
        prompt = build_prompt(
            question="Latest?",
            context="context",
            history=[
                {"q": "Q1", "a": "A1"},
                {"q": "Q2", "a": "A2"},
                {"q": "Q3", "a": "A3"},
                {"q": "Q4", "a": "A4"},
                {"q": "Q5", "a": "A5"},
            ],
        )
        assert "Q1" not in prompt
        assert "Q2" not in prompt
        assert "Q3" in prompt
        assert "Q4" in prompt
        assert "Q5" in prompt

    def test_prompt_returns_string(self):
        prompt = build_prompt(
            question="test",
            context="context",
        )
        assert isinstance(prompt, str)


@pytest.mark.unit
class TestBuildComparePrompt:
    def test_compare_prompt_contains_question(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="Apple data... Tesla data...",
        )
        assert "Compare Apple and Tesla" in prompt

    def test_compare_prompt_contains_context(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="Apple data... Tesla data...",
        )
        assert "Apple data... Tesla data..." in prompt

    def test_compare_prompt_has_business_strategy_section(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="data",
        )
        assert "Business Strategy" in prompt

    def test_compare_prompt_has_ai_technology_section(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="data",
        )
        assert "AI Technology" in prompt

    def test_compare_prompt_has_infrastructure_section(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="data",
        )
        assert "Infrastructure" in prompt

    def test_compare_prompt_has_competitive_advantages_section(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="data",
        )
        assert "Competitive Advantages" in prompt

    def test_compare_prompt_has_risks_section(self):
        prompt = build_compare_prompt(
            question="Compare Apple and Tesla",
            context="data",
        )
        assert "# 5. Risks" in prompt

    def test_compare_prompt_includes_analyst_role(self):
        prompt = build_compare_prompt(
            question="test",
            context="data",
        )
        assert "financial analyst" in prompt

    def test_compare_prompt_returns_string(self):
        prompt = build_compare_prompt(
            question="test",
            context="data",
        )
        assert isinstance(prompt, str)


@pytest.mark.unit
class TestPromptRules:
    def test_prompt_rules_is_string(self):
        assert isinstance(PROMPT_RULES, str)

    def test_prompt_rules_contains_key_instructions(self):
        assert "financial analyst" in PROMPT_RULES
        assert "Evidence" in PROMPT_RULES
        assert "invent facts" in PROMPT_RULES
