"""OpenAI Chat Completions provider."""

from __future__ import annotations

import time
from typing import Any, ClassVar

from openai import OpenAI

from ..providers.base_provider import BaseProvider
from ..providers.provider_config import ProviderConfig
from ..providers.provider_exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderError,
    RateLimitError,
)
from ..providers.provider_models import ChatRequest, ChatResponse, ProviderCapability


class OpenAIProvider(BaseProvider):
    """Text-only adapter for the OpenAI reasoning-model family."""

    MODELS: ClassVar[list[str]] = [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
    ]
    MODEL_CONTEXT_TOKENS: ClassVar[dict[str, int]] = {
        "gpt-5.5": 1_050_000,
        "gpt-5.4": 1_050_000,
        "gpt-5.4-mini": 400_000,
        "gpt-5.4-nano": 400_000,
    }

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._api_key = config.api_key
        self._base_url = config.base_url
        self._model = config.model
        self._max_tokens = config.max_tokens
        self._timeout = config.timeout
        self._max_retry = 3
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            supports_reasoning_effort=True,
            supports_system_prompt=True,
            max_context_tokens=self.MODEL_CONTEXT_TOKENS.get(
                self._model,
                400_000,
            ),
        )

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise AuthenticationError("OpenAI API key is not configured")
            options: dict[str, object] = {
                "api_key": self._api_key,
                "timeout": self._timeout,
                "max_retries": 0,
            }
            if self._base_url:
                options["base_url"] = self._base_url
            self._client = OpenAI(**options)
        return self._client

    @staticmethod
    def _messages(request: ChatRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.messages)
        return messages

    def chat(self, request: ChatRequest) -> ChatResponse:
        client = self._get_client()
        max_tokens = request.max_tokens or self._max_tokens

        for attempt in range(self._max_retry):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=self._messages(request),
                    max_completion_tokens=max_tokens,
                    reasoning_effort="medium",
                )
                choice = response.choices[0]
                usage = response.usage
                return ChatResponse(
                    content=(choice.message.content or "").strip(),
                    provider=self.provider_name,
                    model=self._model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                    metadata={"finish_reason": choice.finish_reason},
                )
            except Exception as exc:
                if self._raise_or_retry(exc, attempt):
                    time.sleep(2**attempt)

        raise ProviderError("OpenAI request failed after retries")

    def _raise_or_retry(self, exc: Exception, attempt: int) -> bool:
        status = getattr(exc, "status_code", None)
        name = type(exc).__name__.lower()
        retryable = status in {408, 429, 500, 502, 503, 504} or any(
            marker in name for marker in ("timeout", "connection")
        )
        if status in {401, 403} or "authentication" in name:
            raise AuthenticationError("OpenAI authentication failed") from exc
        if status == 404 or "notfound" in name:
            raise ModelNotFoundError(f"Model not found: {self._model}") from exc
        if status == 429 or "ratelimit" in name:
            raise RateLimitError("OpenAI rate limit exceeded") from exc
        if retryable and attempt < self._max_retry - 1:
            return True
        if any(marker in name for marker in ("timeout", "connection")):
            raise ProviderConnectionError("Cannot connect to OpenAI") from exc
        raise ProviderError("OpenAI request failed") from exc

    def health(self) -> bool:
        try:
            response = self._get_client().chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_completion_tokens=1,
                reasoning_effort="medium",
            )
            return response is not None
        except Exception:
            return False

    def list_models(self) -> list[str]:
        return list(self.MODELS)
