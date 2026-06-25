from openai import OpenAI
import os
import time
from dotenv import load_dotenv

load_dotenv()

MAX_RETRY = 3


def generate_answer(prompt):
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com"
        ),
        timeout=60
    )

    for attempt in range(MAX_RETRY):

        try:

            response = client.chat.completions.create(

                model=os.getenv(
                    "DEEPSEEK_MODEL",
                    "deepseek-chat"
                ),

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

            return response.choices[0].message.content.strip()

        except Exception as e:

            error = str(e)

            retryable = any([

                "timeout" in error.lower(),

                "connection" in error.lower(),

                "nameresolution" in error.lower(),

                "429" in error,

                "500" in error,

                "503" in error

            ])

            if retryable and attempt < MAX_RETRY - 1:
                wait_time = 2 ** attempt

                print(
                    f"Retry {attempt + 1}/{MAX_RETRY}"
                )

                time.sleep(wait_time)

                continue

            if "timeout" in error.lower():
                return "DeepSeek API Error\n\nRequest timed out."

            if "connection" in error.lower():
                return "DeepSeek API Error\n\nNetwork connection failed."

            if "nameresolution" in error.lower():
                return "DeepSeek API Error\n\nCannot resolve server address."

            if "401" in error:
                return "DeepSeek API Error\n\nInvalid API Key."

            if "402" in error:
                return "DeepSeek API Error\n\nInsufficient balance."

            if "429" in error:
                return "DeepSeek API Error\n\nRate limit exceeded."

            if "500" in error:
                return "DeepSeek API Error\n\nServer error."

            if "503" in error:
                return "DeepSeek API Error\n\nService unavailable."

            return f"API Error:\n{error}"
