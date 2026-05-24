from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProviderResponse:
    content: str
    latency_ms: int
    token_usage: int
    token_usage_estimated: bool
    cost: float
    provider: str

class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> ProviderResponse:
        pass