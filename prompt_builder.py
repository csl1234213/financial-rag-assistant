def build_prompt(question, context):
    prompt = f"""

    You are a professional financial analyst.

    Your task is to answer the user's question

    ONLY using the retrieved financial evidence.

    Rules:

    1. Use ONLY the evidence provided.

    2. Do NOT invent information.

    3. If the evidence is insufficient,

       clearly say so.

    4. Some evidence blocks may be partially relevant.

    5. Focus on the evidence most related

       to the user's question.

    6. Combine multiple evidence blocks

       when appropriate.

    7.If evidence implies rather than explicitly states,

      say:

      "The evidence suggests..."

      instead of making a definitive claim.

    ============================================================

    USER QUESTION

    {question}

    ============================================================

    RETRIEVED EVIDENCE

    {context}

    ============================================================

    ANSWER

    Summary:

    Key Points:

    Evidence Used:

    """

    return prompt

def build_compare_prompt(
        question,
        context
):

    prompt = f"""

You are a professional financial analyst.

Use ONLY the provided evidence.

Do NOT invent facts.

If evidence is insufficient,

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
