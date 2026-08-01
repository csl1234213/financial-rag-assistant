"""Versioned prompt rendering for direct chat and financial RAG workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from prompts.registry import PromptDefinition, PromptRegistry

FINANCIAL_RAG_PROMPT_VERSION = "2.2.0"
FINANCIAL_COMPARE_PROMPT_VERSION = "2.2.0"
DIRECT_CHAT_PROMPT_VERSION = "1.0.0"

FINANCIAL_SYSTEM_PROMPT = "You are a professional financial analyst."

PROMPT_RULES = """
You are a professional financial analyst.

Rules:

1. Answer ONLY using information from the Evidence section.
2. Do NOT invent facts.
3. Do NOT use external knowledge.
4. Write the complete response in the same language as the QUESTION.
   Determine the response language from the QUESTION, not from the Evidence
   or conversation history.
5. If the Evidence does not contain enough information, state that clearly
   in the same language as the QUESTION.
6. When making a statement, cite the Evidence number.
7. Prefer numerical facts whenever available.
8. Separate facts from interpretation.
9. Be concise and objective.
10. Keep evidence citation markers in this exact, language-independent format:
11. For flattened financial tables, align each value with its column header
    from left to right before calculating or describing a period change.
12. A trailing YoY value applies to the row's latest displayed period unless
    the Evidence explicitly maps it to another period.
13. Keep year-over-year and quarter-over-quarter comparisons distinct. Do not
    claim a YoY change for a requested period when its prior-year comparison
    value is absent from the Evidence.

[Evidence 1]
[Evidence 2]

Never use:

(Evidence 1)
(Evidence 2)

Translate response headings when needed, but never translate or alter
[Evidence N] citation markers.
""".strip()

FINANCIAL_RAG_TEMPLATE = f"""
{PROMPT_RULES}

==================================================
CONVERSATION HISTORY
==================================================

{{history_text}}

==================================================
EVIDENCE
==================================================

{{context}}

==================================================
QUESTION
==================================================

{{question}}

==================================================
RESPONSE FORMAT
==================================================

Summary

Key Findings

1.
2.
3.

Risks

1.
2.

Evidence Used

List evidence exactly using:

[Evidence 1]
[Evidence 2]

List all evidence references used.

==================================================

Requirements:

- Use ONLY the Evidence section.
- Never invent facts.
- Never use external knowledge.
- Write all response headings and prose in the same language as the QUESTION.
- Cite evidence numbers.
- Keep citation markers exactly as [Evidence N], regardless of response language.
- Prefer numerical facts.
- If evidence is insufficient, state that clearly in the same language as
  the QUESTION.

==================================================

Answer:
""".strip()

FINANCIAL_COMPARE_TEMPLATE = """
You are a professional financial analyst.

Use ONLY the provided context.
If evidence is insufficient, state that clearly.
Do NOT invent facts.
Write the complete response in the same language as the QUESTION.
When evidence is insufficient, state that in the QUESTION's language.
Keep evidence citation markers exactly as [Evidence N].

==================================================
CONVERSATION HISTORY
==================================================

{history_text}

==================================================
QUESTION
==================================================

{question}

==================================================
RETRIEVED EVIDENCE
==================================================

{context}

==================================================

Compare the companies using EXACTLY the following format.

# 1. Business Strategy

Tesla:
NVIDIA:
Supporting Evidence:

# 2. AI Technology

Tesla:
NVIDIA:
Supporting Evidence:

# 3. Infrastructure

Tesla:
NVIDIA:
Supporting Evidence:

# 4. Competitive Advantages

Tesla:
NVIDIA:
Supporting Evidence:

# 5. Risks

Tesla:
NVIDIA:
Supporting Evidence:

If evidence is missing, state that clearly in the same language as the QUESTION.

# 6. Future Outlook

Tesla:
NVIDIA:
Supporting Evidence:

# 7. Final Comparison

Key Similarities:
Key Differences:

# 8. Investment Implications

Which company appears better positioned?
Why?
Supporting Evidence:

==================================================
Rules
==================================================

1. Use ONLY evidence.
2. Compare BOTH companies.
3. Never skip a section.
4. Reference evidence numbers.
5. Keep answers concise.
6. Do not invent risks.
7. State uncertainty explicitly.
8. Write all response headings and prose in the same language as the QUESTION.
9. Keep citation markers exactly as [Evidence N], regardless of response language.
10. Align flattened table values with their column headers from left to right.
11. Treat a trailing YoY value as applying to the latest displayed period unless
    the evidence explicitly maps it elsewhere.
12. Do not infer a YoY comparison when the corresponding prior-year value is absent.
""".strip()

DIRECT_CHAT_TEMPLATE = """
CONVERSATION HISTORY

{history_text}

User: {question}

Assistant:
""".strip()

_PROMPT_DEFAULTS = {
    "financial_rag": FINANCIAL_RAG_PROMPT_VERSION,
    "financial_compare": FINANCIAL_COMPARE_PROMPT_VERSION,
    "direct_chat": DIRECT_CHAT_PROMPT_VERSION,
}

for _definition in (
    PromptDefinition(
        name="financial_rag",
        version=FINANCIAL_RAG_PROMPT_VERSION,
        content=FINANCIAL_RAG_TEMPLATE,
        system_prompt=FINANCIAL_SYSTEM_PROMPT,
        description="Evidence-grounded financial research response.",
        tags=("rag", "financial", "grounded"),
    ),
    PromptDefinition(
        name="financial_compare",
        version=FINANCIAL_COMPARE_PROMPT_VERSION,
        content=FINANCIAL_COMPARE_TEMPLATE,
        system_prompt=FINANCIAL_SYSTEM_PROMPT,
        description="Evidence-grounded financial comparison response.",
        tags=("rag", "comparison", "financial"),
    ),
    PromptDefinition(
        name="direct_chat",
        version=DIRECT_CHAT_PROMPT_VERSION,
        content=DIRECT_CHAT_TEMPLATE,
        system_prompt=FINANCIAL_SYSTEM_PROMPT,
        description="General assistant response without document retrieval.",
        tags=("direct", "chat"),
    ),
):
    PromptRegistry.register(_definition)


def get_prompt_metadata(
    name: str,
    version: str | None = None,
) -> dict[str, str]:
    return dict(PromptRegistry.metadata(name, version or _PROMPT_DEFAULTS[name]))


def get_prompt_system_prompt(
    name: str,
    version: str | None = None,
) -> str:
    definition = PromptRegistry.get(name, version or _PROMPT_DEFAULTS[name])
    return definition.system_prompt


def _format_history(history: Sequence[dict[str, Any]] | None) -> str:
    if not history:
        return ""

    if any("role" in item or "content" in item for item in history):
        lines: list[str] = []
        for item in history[-8:]:
            role = str(item.get("role", "user")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                lines.append(f"{role.title()}: {content[:1500]}")
        return "\n".join(lines)

    return "\n".join(
        f"Q: {item.get('q', '')}\nA: {item.get('a', '')}"
        for item in history[-3:]
    )


def _render(
    name: str,
    *,
    version: str | None,
    question: str,
    history: Sequence[dict[str, Any]] | None = None,
    context: str = "",
) -> str:
    definition = PromptRegistry.get(name, version or _PROMPT_DEFAULTS[name])
    return definition.content.format(
        question=question,
        context=context,
        history_text=_format_history(history),
    )


def build_prompt(
    question: str,
    context: str,
    history: Sequence[dict[str, Any]] | None = None,
    prompt_version: str | None = None,
) -> str:
    return _render(
        "financial_rag",
        version=prompt_version,
        question=question,
        context=context,
        history=history,
    )


def build_compare_prompt(
    question: str,
    context: str,
    prompt_version: str | None = None,
    *,
    history: Sequence[dict[str, Any]] | None = None,
) -> str:
    return _render(
        "financial_compare",
        version=prompt_version,
        question=question,
        context=context,
        history=history,
    )


def build_direct_chat_prompt(
    question: str,
    history: Sequence[dict[str, Any]] | None = None,
    prompt_version: str | None = None,
) -> str:
    return _render(
        "direct_chat",
        version=prompt_version,
        question=question,
        history=history,
    )
