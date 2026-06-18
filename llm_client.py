from openai import OpenAI
import os
def generate_answer(prompt):

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    try:

        response = client.chat.completions.create(

            model="deepseek-chat",

            messages=[
                {
                    "role": "system",
                    "content": "You are a professional financial analyst."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.2,

            max_tokens=1000

        )

        return response.choices[0].message.content


    except Exception as e:

        error = str(e)

        if "402" in error:
            return """

    DeepSeek API Error


    Reason:

    Insufficient account balance.


    Please recharge your DeepSeek API account.


    """

        return f"API Error:\n{error}"