"""Provider capabilities must describe the implemented adapter contract."""

from llm.adapters.deepseek_provider import DeepSeekProvider
from llm.adapters.gemini_provider import GeminiProvider
from llm.providers.provider_config import ProviderConfig
from llm.providers.provider_models import ProviderCapability
from llm.router import CapabilityRoutingPolicy, TaskType
from llm.router.routing_context import RoutingContext


def _config(provider: str, *, stream: bool = True) -> ProviderConfig:
    return ProviderConfig(
        provider=provider,
        model=f"{provider}-test-model",
        api_key="test-only",
        stream=stream,
    )


def test_deepseek_does_not_advertise_unimplemented_chat_features() -> None:
    capability = DeepSeekProvider(_config("deepseek")).get_capability()

    assert capability.supports_system_prompt is True
    assert capability.supports_stream is False
    assert capability.supports_function_call is False
    assert capability.supports_tools is False
    assert capability.supports_json_mode is False
    assert capability.supports_embedding is False


def test_gemini_text_adapter_does_not_advertise_vendor_only_features() -> None:
    capability = GeminiProvider(_config("gemini")).get_capability()

    assert capability.supports_system_prompt is True
    assert capability.supports_stream is False
    assert capability.supports_function_call is False
    assert capability.supports_tools is False
    assert capability.supports_multimodal is False
    assert capability.supports_image is False
    assert capability.supports_audio is False
    assert capability.supports_video is False
    assert capability.supports_json_mode is False
    assert capability.supports_embedding is False
    assert capability.supports_reasoning_effort is False


def test_capability_policy_rejects_a_partial_required_feature_match() -> None:
    policy = CapabilityRoutingPolicy(
        default_provider="deepseek",
        default_model="deepseek-chat",
    )
    context = RoutingContext(
        task=TaskType.IMAGE_ANALYSIS,
        requires_image=True,
        requires_tools=True,
    )
    capability = ProviderCapability(
        supports_image=True,
        supports_tools=False,
    )

    reason, confidence = policy._match(context, capability, "partial-provider")

    assert reason == "No capability match"
    assert confidence == 0.0
