from fastapi import Depends
from app.core.config import Settings, get_settings
from app.services.ai.base import LLMClient
from app.services.ai.mock_llm import MockLLMClient
from app.services.ai.gemini_llm import GeminiLLMClient

_global_mock_llm = MockLLMClient()


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    """
    Dependency provider that yields the appropriate LLM client adapter.
    Uses MockLLMClient if API key is absent or start with 'mock_',
    otherwise activates GeminiLLMClient.
    """
    api_key = settings.LLM_API_KEY.strip()

    is_mock = (
        not api_key
        or api_key.startswith("mock_")
        or settings.APP_ENV in ("testing", "test")
    )

    if is_mock:
        return _global_mock_llm

    return GeminiLLMClient(
        api_key=api_key,
        model=settings.LLM_MODEL or "gemini-2.5-flash",
    )


__all__ = [
    "LLMClient",
    "MockLLMClient",
    "GeminiLLMClient",
    "get_llm_client",
    "_global_mock_llm",
]
