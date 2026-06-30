# llm/provider.py
# ============================================================
# Legacy adapter — delegates to ProviderFactory
# ============================================================
# This module exists for backward compatibility with existing code
# that calls call_llm(prompt). New code should use:
#
#   from config.llm import LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, ...
#   from llm.factory.provider_factory import ProviderFactory
#   from llm.providers.provider_config import ProviderConfig
#
#   config = ProviderConfig(
#       provider=LLM_PROVIDER,
#       model=LLM_MODEL,
#       api_key=LLM_API_KEY,
#       ...
#   )
#   provider = ProviderFactory.create(config)
#   response = provider.chat(ChatRequest(...))
# ============================================================

from config.llm import (
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_STREAM,
)
from .factory.provider_factory import ProviderFactory
from .providers.provider_config import ProviderConfig
from .providers.provider_models import ChatRequest
from .adapters.deepseek_provider import DeepSeekProvider
from .adapters.gemini_provider import GeminiProvider
from .providers.provider_registry import ProviderRegistry

# Register providers at import time
ProviderRegistry.register("deepseek", DeepSeekProvider)
ProviderRegistry.register("gemini", GeminiProvider)


def _build_config() -> ProviderConfig:
    return ProviderConfig(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        timeout=LLM_TIMEOUT,
        stream=LLM_STREAM,
    )


def call_llm(prompt: str) -> str:
    config = _build_config()
    provider = ProviderFactory.create(config)
    request = ChatRequest(
        messages=[{
            "role": "user",
            "content": prompt
        }],
        system_prompt="You are a professional financial analyst.",
        temperature=0.2,
        max_tokens=1000
    )
    response = provider.chat(request)
    return response.content