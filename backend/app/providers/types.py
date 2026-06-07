from dataclasses import dataclass
from typing import Literal

ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class CostEstimate:
    input_usd: float
    output_usd: float
    total_usd: float
    pricing_source: str


@dataclass(frozen=True)
class ChatCompletionRequest:
    messages: list[ChatMessage]
    max_output_tokens: int = 300


@dataclass(frozen=True)
class ChatCompletionResult:
    provider: str
    model: str
    content: str
    usage: TokenUsage
    cost: CostEstimate
    mock: bool = False


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False
