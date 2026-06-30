# ============================================================
# DeepSeek Provider
# ============================================================
# DeepSeek uses OpenAI-compatible API, so we reuse openai-python SDK.
# All settings come from ProviderConfig, not from environment variables.
# ============================================================

import time
from typing import List
from openai import OpenAI
from ..providers.base_provider import BaseProvider
from ..providers.provider_config import ProviderConfig
from ..providers.provider_models import (
    ChatRequest,
    ChatResponse,
    ProviderCapability,
)
from ..providers.provider_exceptions import (
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderError,
)


class DeepSeekProvider(BaseProvider):

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._api_key = config.api_key
        self._base_url = config.base_url or "https://api.deepseek.com"
        self._model = config.model
        self._temperature = config.temperature
        self._max_tokens = config.max_tokens
        self._timeout = config.timeout
        self._stream = config.stream
        self._max_retry = 3
        self._client = None
        self._provider_name = "deepseek"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            supports_stream=self._stream,
            supports_function_call=True,
            supports_image=False,
            supports_audio=False,
            supports_video=False,
            supports_json_mode=True,
            supports_embedding=True,
            supports_reranking=False,
            supports_reasoning_effort=False,
            supports_system_prompt=True,
            supports_tools=True,
            supports_multimodal=False,
            max_context_tokens=128000
        )

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise AuthenticationError(
                    "DEEPSEEK_API_KEY not set in environment"
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout
            )
        return self._client

    def chat(self, request: ChatRequest) -> ChatResponse:
        client = self._get_client()
        messages = []

        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        messages.extend(request.messages)

        model = self._model
        temperature = request.temperature
        max_tokens = request.max_tokens or self._max_tokens

        for attempt in range(self._max_retry):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                choice = response.choices[0]
                usage = response.usage

                return ChatResponse(
                    content=choice.message.content.strip() if choice.message.content else "",
                    provider=self._provider_name,
                    model=model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                    metadata={
                        "finish_reason": choice.finish_reason,
                    }
                )

            except Exception as e:
                error_str = str(e).lower()

                retryable = any([
                    "timeout" in error_str,
                    "connection" in error_str,
                    "nameresolution" in error_str,
                    "429" in error_str,
                    "500" in error_str,
                    "503" in error_str,
                ])

                if "401" in error_str or "unauthorized" in error_str:
                    raise AuthenticationError("Invalid DeepSeek API key") from e
                elif "402" in error_str:
                    raise RateLimitError("Insufficient balance") from e
                elif "429" in error_str:
                    raise RateLimitError("Rate limit exceeded") from e
                elif "404" in error_str or "model not found" in error_str:
                    raise ModelNotFoundError(f"Model not found: {model}") from e
                elif "connection" in error_str or "timeout" in error_str:
                    if not retryable or attempt >= self._max_retry - 1:
                        raise ProviderConnectionError(
                            f"Cannot connect to DeepSeek: {str(e)}"
                        ) from e
                else:
                    if not retryable or attempt >= self._max_retry - 1:
                        raise ProviderError(
                            f"DeepSeek error: {str(e)}"
                        ) from e

                if retryable and attempt < self._max_retry - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue

        raise ProviderError("Max retries exceeded")

    def health(self) -> bool:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._model,
                messages=[{
                    "role": "user",
                    "content": "ping"
                }],
                max_tokens=5,
            )
            return response is not None
        except Exception:
            return False

    def list_models(self) -> List[str]:
        return [
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-coder",
        ]