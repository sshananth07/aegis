import structlog
from typing import Optional
from app.core.config import settings
from app.providers.base import BaseProvider, ProviderResponse
from app.providers.ollama import OllamaProvider
from app.providers.gemini import GeminiProvider

logger = structlog.get_logger()

PROVIDER_MAP = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
}

FALLBACK_CHAIN = {
    "gemini": "ollama",
    "ollama": None,
}

MAX_RETRIES = 2

class ProviderRouter:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def _provider_enabled(self, name: str) -> bool:
        return name != "ollama" or settings.ollama_enabled

    def _fallback_for(self, name: str) -> Optional[str]:
        fallback = FALLBACK_CHAIN.get(name)
        if fallback and self._provider_enabled(fallback):
            return fallback
        return None

    def _get_provider(self, name: str) -> BaseProvider:
        if not self._provider_enabled(name):
            raise ValueError(
                "Ollama is disabled. Set OLLAMA_ENABLED=true for local/self-host mode."
            )
        cls = PROVIDER_MAP.get(name)
        if not cls:
            raise ValueError(f"Unknown provider: {name}")
        return cls()

    async def route(
        self,
        prompt: str,
        on_event: Optional[callable] = None
    ) -> tuple[ProviderResponse, list[dict]]:
        """
        Returns (response, events)
        events is a list of trace event dicts
        """
        events = []
        current_provider = self.provider_name

        def emit(event_type: str, provider: str, **kwargs):
            event = {"event_type": event_type, "provider": provider, **kwargs}
            events.append(event)
            logger.info(event_type, provider=provider, **kwargs)

        while current_provider:
            provider = self._get_provider(current_provider)
            emit("provider_selected", current_provider)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await provider.generate(prompt)
                    emit("provider_succeeded", current_provider,
                         latency_ms=response.latency_ms)
                    return response, events

                except Exception as e:
                    emit("provider_failed", current_provider,
                         error=str(e), attempt=attempt)

                    if attempt < MAX_RETRIES:
                        emit("retry_triggered", current_provider,
                             attempt=attempt)
                    else:
                        # All retries exhausted, try fallback
                        fallback = self._fallback_for(current_provider)
                        if fallback:
                            emit("fallback_triggered", current_provider,
                                 fallback_provider=fallback)
                            current_provider = fallback
                            break
                        else:
                            emit("provider_failed", current_provider,
                                 error="No fallback available")
                            raise RuntimeError(
                                f"All providers failed. Last error: {e}"
                            )

        raise RuntimeError("Provider routing exhausted")
