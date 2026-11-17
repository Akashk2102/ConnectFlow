import json
import logging
from typing import Optional
import httpx
from app.schemas.ai import LLMClassificationResult
from app.services.ai.base import LLMClient
from app.services.ai.mock_llm import MockLLMClient

logger = logging.getLogger(__name__)


SYSTEM_CLASSIFICATION_PROMPT = """
You are an expert customer communication intelligence classifier for ConnectFlow.
Analyze the inbound customer message and return a strictly valid JSON object matching this schema:
{
  "intent": "order_inquiry" | "refund_request" | "support_ticket" | "faq_general" | "unknown",
  "confidence_score": float between 0.0 and 1.0,
  "sentiment": "positive" | "neutral" | "negative" | "frustrated",
  "urgency": "low" | "medium" | "high",
  "extracted_entities": { "order_id": "string", "email": "string" },
  "requires_tool": boolean,
  "suggested_tool": "fetch_order_status" | "create_support_ticket" | "issue_refund" | null,
  "suggested_reply": "Friendly, professional draft response to the customer."
}
Do not include markdown fences or explanation. Return ONLY raw JSON.
"""


class GeminiLLMClient(LLMClient):
    """
    Google Gemini REST API Client.
    Uses asynchronous HTTPS requests with structured JSON mode.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self._custom_client = http_client
        self.timeout = timeout
        self._fallback = MockLLMClient()

    async def classify_message(
        self,
        message_text: str,
        customer_name: Optional[str] = None,
        conversation_history: Optional[str] = None,
    ) -> LLMClassificationResult:
        if not self.api_key or self.api_key.startswith("mock_"):
            return await self._fallback.classify_message(message_text, customer_name, conversation_history)

        prompt_payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"Customer Name: {customer_name or 'Unknown'}"},
                        {"text": f"Recent Conversation History:\n{conversation_history or 'None'}"},
                        {"text": f"Inbound Message: \"{message_text}\""},
                    ],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_CLASSIFICATION_PROMPT}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            url = f"{self.base_url}?key={self.api_key}"
            if self._custom_client:
                response = await self._custom_client.post(url, json=prompt_payload, timeout=self.timeout)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=prompt_payload)

            if response.status_code == 200:
                data = response.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(raw_text)
                return LLMClassificationResult.model_validate(parsed_json)
            else:
                logger.warning(f"Gemini API returned status {response.status_code}: {response.text}. Using fallback.")
                return await self._fallback.classify_message(message_text, customer_name, conversation_history)

        except Exception as exc:
            logger.error(f"Error calling Gemini API: {exc}. Falling back to deterministic classifier.")
            return await self._fallback.classify_message(message_text, customer_name, conversation_history)

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
    ) -> str:
        if not self.api_key or self.api_key.startswith("mock_"):
            return await self._fallback.generate_response(system_prompt, user_message, context)

        prompt_payload = {
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": 0.7},
        }

        try:
            url = f"{self.base_url}?key={self.api_key}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=prompt_payload)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as exc:
            logger.error(f"Error in Gemini generate_response: {exc}")

        return await self._fallback.generate_response(system_prompt, user_message, context)
