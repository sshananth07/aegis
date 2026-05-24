import time
import httpx
from app.providers.base import BaseProvider, ProviderResponse
from app.core.config import settings

class OllamaProvider(BaseProvider):
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.base_url = settings.ollama_host

    async def generate(self, prompt: str) -> ProviderResponse:
        start = time.time()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "keep_alive": 0
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = int((time.time() - start) * 1000)
        content = data["message"]["content"]
        token_usage = data.get("eval_count", 0)
        # Ollama provides real token counts
        token_usage_estimated = token_usage == 0

        return ProviderResponse(
            content=content,
            latency_ms=latency_ms,
            token_usage=token_usage,
            token_usage_estimated=token_usage_estimated,
            cost=0.0,
            provider="ollama"
        )
