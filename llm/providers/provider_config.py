# ============================================================
# ProviderConfig — Configuration-driven provider init
# ============================================================
# Each provider is created from a ProviderConfig, not from
# scattered environment variable reads inside the provider.
# ============================================================

from dataclasses import dataclass
from math import ceil


def timeout_budget_for_provider(
    provider: str,
    *,
    timeout: int,
    read_timeout: float | None,
    total_deadline: float | None,
) -> tuple[int, float | None]:
    """Keep local Ollama inference bounded by, but not shorter than, the request deadline.

    Global HTTP defaults are tuned for remote APIs (60s total / 45s read),
    while a local model may need longer for prompt evaluation and generation.
    The absolute request deadline remains the hard ceiling in the adapter.
    """
    if provider.casefold() != "ollama" or not total_deadline or total_deadline <= 0:
        return timeout, read_timeout
    deadline_budget = float(total_deadline)
    return (
        max(timeout, ceil(deadline_budget)),
        max(float(read_timeout or timeout), deadline_budget),
    )


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
    connect_timeout: float | None = None
    read_timeout: float | None = None
    total_deadline: float | None = None
