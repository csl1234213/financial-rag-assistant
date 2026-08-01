# ============================================================
# Model Router — Core Orchestrator
# ============================================================
# The ModelRouter only orchestrates — it does NOT make decisions.
#
# Decision logic lives in Policy (e.g. CapabilityRoutingPolicy).
# Provider knowledge lives in Registry.
# Provider creation lives in Factory.
#
# ModelRouter ONLY:
#   1. Calls Policy   → get RoutingResult
#   2. Calls Factory  → get Provider instance
#   3. Returns both
# ============================================================

import time

from config.llm import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DOUBAO_API_KEY,
    DOUBAO_BASE_URL,
    GEMINI_API_KEY,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_STREAM,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

from ..factory.provider_factory import ProviderFactory
from ..providers.provider_config import ProviderConfig
from ..providers.provider_registry import ProviderRegistry
from .routing_context import RoutingContext
from .routing_policy import RoutingPolicy
from .routing_result import RoutingResult

# Provider-specific config overrides.
# Router uses this to build the correct ProviderConfig for each provider.
# This is DATA, not routing logic — it maps provider names to their
# API keys and base URLs.
_PROVIDER_CONFIG_OVERRIDES = {
    "deepseek": {
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_BASE_URL,
    },
    "gemini": {
        "api_key": GEMINI_API_KEY,
    },
    "openai": {
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_BASE_URL,
    },
    "anthropic": {
        "api_key": ANTHROPIC_API_KEY,
        "base_url": ANTHROPIC_BASE_URL,
    },
    "doubao": {
        "api_key": DOUBAO_API_KEY,
        "base_url": DOUBAO_BASE_URL,
    },
}


class ModelRouter:
    def __init__(
        self,
        policy: RoutingPolicy,
        provider_configs: dict | None = None,
        available_providers: list[str] | None = None,
    ):
        self._policy = policy
        self._provider_configs = provider_configs or _PROVIDER_CONFIG_OVERRIDES
        self._available_providers = (
            tuple(available_providers)
            if available_providers is not None
            else None
        )

    def route(
        self,
        context: RoutingContext,
    ) -> dict:
        registered_providers = ProviderRegistry.list_providers()
        providers = (
            [
                provider
                for provider in registered_providers
                if provider in self._available_providers
            ]
            if self._available_providers is not None
            else registered_providers
        )
        if not providers:
            raise ValueError("No configured LLM provider is available")

        t0 = time.perf_counter()
        result: RoutingResult = self._policy.select(
            context=context,
            providers=providers,
        )
        decision_time_ms = (time.perf_counter() - t0) * 1000

        result.decision_time_ms = round(decision_time_ms, 3)

        config = self._build_config(result)

        provider = ProviderFactory.create(config)

        return {
            "provider": provider,
            "routing": result,
        }

    def _build_config(
        self,
        result: RoutingResult,
    ) -> ProviderConfig:
        overrides = self._provider_configs.get(
            result.provider,
            {},
        )
        return ProviderConfig(
            provider=result.provider,
            model=result.model,
            api_key=overrides.get("api_key", LLM_API_KEY),
            base_url=overrides.get("base_url", LLM_BASE_URL),
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            stream=LLM_STREAM,
        )
