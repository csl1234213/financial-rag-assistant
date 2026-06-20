def build_prompt(question, context, history = None):
    history_text = ""
    history_lines = []

    if history:
        for h in history[-3:]:
            history_lines.append(

                f"Q: {h['q']}\nA: {h['a']}"

            )

        history_text = "\n".join(history_lines)

    prompt = f"""
    You are a financial analyst.
    {PROMPT_RULES}

    Conversation History:
    {history_text}

    Question:
    {question}

    Context:
    {context}
    """

    return prompt

def build_compare_prompt(
        question,
        context
):

    prompt = f"""

You are a professional financial analyst.

Use ONLY the provided context.

If evidence is insufficient,

state that clearly.

Do NOT invent facts.

say:

"Insufficient evidence."

==================================================

QUESTION

{question}

==================================================

RETRIEVED EVIDENCE

{context}

==================================================

Compare the companies.

Use EXACTLY the following format.

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

If evidence is missing,

say:

Insufficient evidence.

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

Rules:

1.

Use ONLY evidence.

2.

Compare BOTH companies.

3.

Never skip a section.

4.

Reference evidence numbers.

5.

Keep answers concise.

6.

Do not invent risks.

7.

State uncertainty explicitly.

"""

    return prompt
