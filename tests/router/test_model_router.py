import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from unittest.mock import MagicMock

import pytest

from llm.router import (
    ModelRouter,
    RoutingPolicy,
    TaskType,
)
from llm.router.routing_context import RoutingContext
from llm.router.routing_result import RoutingResult
from llm.providers.provider_registry import ProviderRegistry
from llm.providers.base_provider import BaseProvider
from llm.providers.provider_config import ProviderConfig
from llm.providers.provider_models import (
    ChatRequest,
    ChatResponse,
    ProviderCapability,
)


class _MockProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        self._config = config

    @property
    def provider_name(self) -> str:
        return self._config.provider

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content="mock",
            provider=self._config.provider,
            model=self._config.model,
        )

    def health(self) -> bool:
        return True

    def list_models(self) -> list:
        return [self._config.model]

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            supports_stream=True,
            supports_tools=True,
            max_context_tokens=8192,
        )


class TestModelRouter:

    @pytest.fixture(autouse=True)
    def _setup_registry(self):
        ProviderRegistry.clear()
        ProviderRegistry.register("deepseek", _MockProvider)
        ProviderRegistry.register("gemini", _MockProvider)
        yield
        ProviderRegistry.clear()

    @pytest.fixture
    def context(self):
        return RoutingContext(task=TaskType.CHAT)

    @pytest.fixture
    def router(self):
        policy = MagicMock()
        policy.select.return_value = RoutingResult(
            provider="deepseek",
            model="deepseek-chat",
            reason="Default provider",
            confidence=0.7,
        )
        return ModelRouter(
            policy=RoutingPolicy(policy),
            provider_configs={
                "deepseek": {
                    "api_key": "test-deepseek-key",
                    "base_url": "https://test.deepseek.com",
                },
                "gemini": {
                    "api_key": "test-gemini-key",
                },
            },
        )

    # =========================
    # route()
    # =========================

    def test_route_returns_provider_and_routing(self, router, context):
        result = router.route(context)

        assert "provider" in result
        assert "routing" in result
        assert isinstance(result["provider"], BaseProvider)
        assert isinstance(result["routing"], RoutingResult)

    def test_route_sets_decision_time_ms(self, router, context):
        result = router.route(context)

        assert result["routing"].decision_time_ms is not None
        assert result["routing"].decision_time_ms >= 0.0

    def test_route_routing_matches_policy(self, router, context):
        result = router.route(context)

        assert result["routing"].provider == "deepseek"
        assert result["routing"].model == "deepseek-chat"
        assert result["routing"].reason == "Default provider"
        assert result["routing"].confidence == 0.7

    # =========================
    # _build_config()
    # =========================

    def test_build_config_uses_provider_overrides(self, router, context):
        result = router.route(context)

        provider = result["provider"]
        assert provider._config.api_key == "test-deepseek-key"
        assert provider._config.base_url == "https://test.deepseek.com"

    def test_build_config_gemini_uses_override(self, router, context):
        policy = router._policy._policy
        policy.select.return_value = RoutingResult(
            provider="gemini",
            model="gemini-2.5-flash",
            reason="Gemini selected",
            confidence=0.95,
        )

        result = router.route(context)

        provider = result["provider"]
        assert provider._config.api_key == "test-gemini-key"

    def test_build_config_falls_back_to_default(self):
        policy = MagicMock()
        policy.select.return_value = RoutingResult(
            provider="deepseek",
            model="deepseek-chat",
            reason="Default provider",
            confidence=0.5,
        )
        router = ModelRouter(
            policy=RoutingPolicy(policy),
            provider_configs={},
        )

        result = router.route(RoutingContext(task=TaskType.CHAT))

        provider = result["provider"]
        assert provider._config.provider == "deepseek"
        assert provider._config.model == "deepseek-chat"

    # =========================
    # route() with custom provider_configs
    # =========================

    def test_custom_provider_configs(self, context):
        policy = MagicMock()
        policy.select.return_value = RoutingResult(
            provider="deepseek",
            model="deepseek-reasoner",
            reason="Custom config",
            confidence=1.0,
        )
        router = ModelRouter(
            policy=RoutingPolicy(policy),
            provider_configs={
                "deepseek": {
                    "api_key": "custom-key",
                    "base_url": "https://custom.deepseek.com",
                },
            },
        )

        result = router.route(context)

        assert result["provider"]._config.api_key == "custom-key"
        assert result["provider"]._config.base_url == "https://custom.deepseek.com"

    # =========================
    # decision_time_ms
    # =========================

    def test_decision_time_ms_is_positive_float(self, router, context):
        result = router.route(context)

        dt = result["routing"].decision_time_ms
        assert isinstance(dt, float)
        assert dt >= 0.0

    def test_decision_time_ms_is_rounded(self, router, context):
        result = router.route(context)

        dt = result["routing"].decision_time_ms
        assert dt == round(dt, 3)

    # =========================
    # RoutingResult fields on route()
    # =========================

    def test_routing_result_fallback_in_route(self, router, context):
        result = router.route(context)

        assert hasattr(result["routing"], "fallback_provider")
        assert hasattr(result["routing"], "decision_time_ms")