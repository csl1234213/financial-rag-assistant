"""Native Ollama chat adapter for local, provider-cost-free evaluation."""

from __future__ import annotations

import time

import httpx

from ..providers.base_provider import BaseProvider
from ..providers.provider_config import ProviderConfig
from ..providers.provider_exceptions import (
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
)
from ..providers.provider_guard import normalize_local_ollama_url
from ..providers.provider_models import ChatRequest, ChatResponse, ProviderCapability


class OllamaProvider(BaseProvider):
    """Call Ollama's native ``/api/chat`` endpoint without OpenAI shims."""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._model = config.model
        self._base_url = (config.base_url or "http://host.docker.internal:11434").rstrip("/")
        self._timeout = config.timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            supports_system_prompt=True,
            max_context_tokens=8192,
        )

    def _validate_local_endpoint(self) -> None:
        try:
            self._base_url = normalize_local_ollama_url(self._base_url)
        except ValueError as exc:
            raise ProviderError("Ollama provider requires an explicitly local endpoint") from exc

    def _timeout_config(self, request: ChatRequest | None = None) -> httpx.Timeout:
        remaining = self._config.total_deadline
        if request is not None and request.deadline is not None:
            request_remaining = request.deadline - time.monotonic()
            if request_remaining <= 0:
                raise ProviderTimeoutError("Ollama request exceeded its total deadline")
            remaining = min(remaining, request_remaining) if remaining else request_remaining
        if remaining is not None:
            remaining = max(0.001, min(float(remaining), float(self._timeout)))
        else:
            remaining = float(self._timeout)
        connect = min(float(self._config.connect_timeout or remaining), remaining)
        read = min(float(self._config.read_timeout or remaining), remaining)
        return httpx.Timeout(remaining, connect=connect, read=read)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self._validate_local_endpoint()
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.messages)
        options = {
            "temperature": request.temperature,
            "num_ctx": self.get_capability().max_context_tokens,
            "num_predict": request.max_tokens or self._config.max_tokens,
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "think": False,
            "stream": False,
            "options": options,
        }
        started = time.monotonic()
        try:
            with httpx.Client(timeout=self._timeout_config(request)) as client:
                response = client.post(f"{self._base_url}/api/chat", json=payload)
                if response.status_code == 404:
                    raise ModelNotFoundError(f"Ollama model or endpoint not found: {self._model}")
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Ollama request timed out") from exc
        except httpx.ConnectError as exc:
            raise ProviderConnectionError("Cannot connect to local Ollama") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError("Ollama request failed") from exc
        except (httpx.RequestError, ValueError) as exc:
            raise ProviderError("Ollama returned an invalid response") from exc

        message = body.get("message")
        content = message.get("content", "").strip() if isinstance(message, dict) else ""
        if not content:
            raise ProviderError("Ollama returned empty model content")
        prompt_tokens = int(body.get("prompt_eval_count") or 0)
        completion_tokens = int(body.get("eval_count") or 0)
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=str(body.get("model") or self._model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            metadata={
                "done_reason": body.get("done_reason"),
                "latency_seconds": round(time.monotonic() - started, 3),
            },
        )

    def health(self) -> bool:
        try:
            self._validate_local_endpoint()
            with httpx.Client(timeout=self._timeout_config()) as client:
                response = client.get(f"{self._base_url}/api/tags")
                return response.is_success
        except (httpx.RequestError, ProviderError):
            return False

    def list_models(self) -> list[str]:
        return [self._model]
