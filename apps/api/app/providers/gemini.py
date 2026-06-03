import time
import httpx
from app.providers.base import BaseProvider, ProviderResponse
from app.core.config import settings

COST_PER_1K_INPUT = 0.00025
COST_PER_1K_OUTPUT = 0.0005

class GeminiProvider(BaseProvider):
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str) -> ProviderResponse:
        start = time.time()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 1024}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = int((time.time() - start) * 1000)
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)
        # Gemini provides real token counts via usageMetadata
        token_usage_estimated = total_tokens == 0
        cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + \
               (output_tokens / 1000 * COST_PER_1K_OUTPUT)

        return ProviderResponse(
            content=content,
            latency_ms=latency_ms,
            token_usage=total_tokens,
            token_usage_estimated=token_usage_estimated,
            cost=cost,
            provider="gemini"
        )
