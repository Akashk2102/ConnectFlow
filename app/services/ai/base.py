from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.ai import LLMClassificationResult


class LLMClient(ABC):
    """
    Abstract interface for LLM providers (Gemini, OpenAI, Mock).
    Decouples business logic from specific AI provider SDKs.
    """

    @abstractmethod
    async def classify_message(
        self,
        message_text: str,
        customer_name: Optional[str] = None,
        conversation_history: Optional[str] = None,
    ) -> LLMClassificationResult:
        """
        Classifies incoming message intent, sentiment, urgency, and extracts entities.
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
    ) -> str:
        """
        Synthesizes a natural language response based on system instructions and context.
        """
        pass
