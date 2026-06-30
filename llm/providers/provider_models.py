# ============================================================
# Provider Models — Unified Request / Response
# ============================================================
# All LLM providers return the same ChatResponse object,
# regardless of the underlying SDK (DeepSeek, Claude, Gemini, etc.)
# ============================================================

from dataclasses import dataclass, field


@dataclass
class ProviderCapability:
    """Provider capabilities abstraction.

    Agent Runtime can make decisions based on capabilities instead of
    checking if provider == "deepseek", which makes the code cleaner
    and supports future providers without changes.

    Each provider declares its own capabilities truthfully.
    Planner / Agent uses these fields to auto-select the best provider.
    """
    supports_stream: bool = False
    supports_function_call: bool = False
    supports_image: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    supports_json_mode: bool = False
    supports_embedding: bool = False
    supports_reranking: bool = False
    supports_reasoning_effort: bool = False
    supports_system_prompt: bool = False
    supports_tools: bool = False
    supports_multimodal: bool = False
    max_context_tokens: int = 4096


@dataclass
class ChatRequest:
    messages: list
    temperature: float = 0.0
    max_tokens: int | None = None
    system_prompt: str | None = None


@dataclass
class ChatResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: dict = field(default_factory=dict)