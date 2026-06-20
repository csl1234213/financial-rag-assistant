from openai import OpenAI
import os

def generate_answer(prompt):

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com"
        ),
        timeout = 60
    )

    try:

        response = client.chat.completions.create(

            model=os.getenv("DEEPSEEK_MODEL","deepseek-chat"),

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
        content = response.choices[0].message.content
        return content.strip()


    except Exception as e:

        error = str(e)

        if "timeout" in error.lower():
            return """

        DeepSeek API Error

        Request timed out.

        Please check your network and retry.

        """

        if "connection" in error.lower():
            return """

        DeepSeek API Error

        Network connection failed.

        Please check your Internet.

        """

        if "nameresolution" in error.lower():
            return """

        DeepSeek API Error

        Cannot resolve server address.

        Please check DNS or proxy settings.

        """

        if "401" in error:
            return """

        DeepSeek API Error

        Invalid API Key.

        """


        if "402" in error:
            return """

        DeepSeek API Error

        Insufficient balance.

        Please recharge your account.

        """


        if "429" in error:
            return """

        DeepSeek API Error

        Rate limit exceeded.

        Please retry later.

        """

        if "500" in error:
            return """

        DeepSeek API Error

        Server error.

        Please retry later.

        """

        if "503" in error:
            return """

        DeepSeek API Error

        Service unavailable.

        Please retry later.

        """

        return f"API Error:\n{error}"