# llm/provider.py

from llm.deepseek import generate_answer

def call_llm(prompt):
    return generate_answer(prompt)