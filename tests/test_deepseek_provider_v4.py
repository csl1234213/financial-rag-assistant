from types import SimpleNamespace

from llm.adapters.deepseek_provider import DeepSeekProvider
from llm.providers.provider_config import ProviderConfig
from llm.providers.provider_models import ChatRequest


def test_v4_chat_uses_the_official_thinking_request_contract() -> None:
    calls: list[dict[str, object]] = []

    def create_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="final answer"),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=12,
                completion_tokens=8,
                total_tokens=20,
            ),
        )

    provider = DeepSeekProvider(
        ProviderConfig(
            provider="deepseek",
            model="deepseek-v4-pro",
            api_key="test-only-key",
            temperature=0.7,
        )
    )
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_completion),
        )
    )

    response = provider.chat(
        ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
        )
    )

    assert response.content == "final answer"
    assert response.model == "deepseek-v4-pro"
    assert calls == [
        {
            "model": "deepseek-v4-pro",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 4096,
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
    ]


def test_v4_empty_length_response_recovers_with_bounded_answer_request() -> None:
    calls: list[dict[str, object]] = []

    def create_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=""),
                        finish_reason="length",
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=4096,
                    total_tokens=4106,
                ),
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="recovered answer"),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=12,
                total_tokens=22,
            ),
        )

    provider = DeepSeekProvider(
        ProviderConfig(
            provider="deepseek",
            model="deepseek-v4-flash",
            api_key="test-only-key",
            max_tokens=8192,
        )
    )
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_completion),
        )
    )

    response = provider.chat(
        ChatRequest(
            messages=[{"role": "user", "content": "Summarize the filing"}],
            max_tokens=8192,
        )
    )

    assert response.content == "recovered answer"
    assert len(calls) == 2
    assert calls[0]["extra_body"] == {"thinking": {"type": "enabled"}}
    assert calls[1]["max_tokens"] == 2048
    assert calls[1]["extra_body"] == {"thinking": {"type": "disabled"}}
