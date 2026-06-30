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
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_STREAM,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    GEMINI_API_KEY,
)
from ..providers.provider_registry import ProviderRegistry
from ..providers.provider_config import ProviderConfig
from ..factory.provider_factory import ProviderFactory

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
}


class ModelRouter:

    def __init__(
        self,
        policy: RoutingPolicy,
        provider_configs: dict | None = None,
    ):
        self._policy = policy
        self._provider_configs = (
            provider_configs or _PROVIDER_CONFIG_OVERRIDES
        )

    def route(
        self,
        context: RoutingContext,
    ) -> dict:
        providers = ProviderRegistry.list_providers()

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