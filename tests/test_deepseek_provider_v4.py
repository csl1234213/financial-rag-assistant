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
