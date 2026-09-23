from typing import Optional
from src.core.config import settings
from src.providers.base import AIProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.ollama_provider import OllamaProvider

def get_ai_provider(provider_type: Optional[str] = None, model: Optional[str] = None) -> AIProvider:
    """
    Factory function returning the appropriate AI provider instance.
    Defaults to settings.ai_provider ("gemini" or "ollama").
    """
    choice = (provider_type or settings.ai_provider or "gemini").lower().strip()

    if choice == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=model or settings.ollama_model,
            vision_model=settings.ollama_vision_model
        )
    elif choice == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=model or settings.gemini_model
        )
    else:
        raise ValueError(f"Unknown AI Provider '{choice}'. Supported providers: 'gemini', 'ollama'")
