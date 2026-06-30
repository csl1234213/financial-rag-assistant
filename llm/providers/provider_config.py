# ============================================================
# ProviderConfig — Configuration-driven provider init
# ============================================================
# Each provider is created from a ProviderConfig, not from
# scattered environment variable reads inside the provider.
# ============================================================

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 60
    stream: bool = False