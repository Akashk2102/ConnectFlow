import re
from typing import Optional
from app.schemas.ai import (
    IntentCategory,
    LLMClassificationResult,
    Sentiment,
    Urgency,
)
from app.services.ai.base import LLMClient

# Regex patterns for entity extraction
ORDER_ID_PATTERN = re.compile(r"\b(?:ORD[-_]?\d+|#\d{3,8}|order\s+#?(\d+))\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class MockLLMClient(LLMClient):
    """
    Deterministic rule-based LLM simulator for testing and zero-cost local development.
    Extracts entities and categorizes intents with 100% predictable outputs.
    """

    async def classify_message(
        self,
        message_text: str,
        customer_name: Optional[str] = None,
        conversation_history: Optional[str] = None,
    ) -> LLMClassificationResult:
        text_lower = message_text.lower()
        extracted_entities = {}

        # 1. Entity Extraction (Order ID, Email)
        order_match = ORDER_ID_PATTERN.search(message_text)
        if order_match:
            extracted_entities["order_id"] = order_match.group(0).upper().replace(" ", "")

        email_match = EMAIL_PATTERN.search(message_text)
        if email_match:
            extracted_entities["email"] = email_match.group(0)

        # 2. Sentiment & Urgency Analysis
        sentiment = Sentiment.NEUTRAL
        urgency = Urgency.MEDIUM

        if any(w in text_lower for w in ["angry", "furious", "terrible", "awful", "horrible", "unacceptable"]):
            sentiment = Sentiment.FRUSTRATED
            urgency = Urgency.HIGH
        elif any(w in text_lower for w in ["asap", "urgent", "emergency", "immediately"]):
            urgency = Urgency.HIGH
        elif any(w in text_lower for w in ["thank", "great", "awesome", "perfect", "good"]):
            sentiment = Sentiment.POSITIVE
            urgency = Urgency.LOW

        # 3. Intent Classification & Tool Suggestion
        if any(w in text_lower for w in ["refund", "cancel", "money back", "return item"]):
            intent = IntentCategory.REFUND_REQUEST
            requires_tool = True
            suggested_tool = "issue_refund"
            suggested_reply = "I understand you would like to request a refund. Let me pull up your order details."

        elif any(w in text_lower for w in ["where is", "track", "tracking", "status", "shipping", "shipped", "package", "delivery"]) or "order_id" in extracted_entities:
            intent = IntentCategory.ORDER_INQUIRY
            requires_tool = True
            suggested_tool = "fetch_order_status"
            order_ref = extracted_entities.get("order_id", "your order")
            suggested_reply = f"Checking the latest delivery status for {order_ref} right away."

        elif any(w in text_lower for w in ["broken", "not working", "defective", "damaged", "error", "bug", "issue", "agent"]):
            intent = IntentCategory.SUPPORT_TICKET
            requires_tool = True
            suggested_tool = "create_support_ticket"
            suggested_reply = "I'm sorry to hear you're experiencing issues. I am opening a support ticket for our engineering team."

        elif any(w in text_lower for w in ["hours", "open", "location", "address", "policy", "hi", "hello"]):
            intent = IntentCategory.FAQ_GENERAL
            requires_tool = False
            suggested_tool = None
            suggested_reply = "Hello! ConnectFlow is open Monday through Friday, 9am to 6pm EST. How can I help you today?"

        else:
            intent = IntentCategory.UNKNOWN
            requires_tool = False
            suggested_tool = None
            suggested_reply = "Thank you for reaching out. A customer support representative will review your message shortly."

        return LLMClassificationResult(
            intent=intent,
            confidence_score=0.95 if intent != IntentCategory.UNKNOWN else 0.50,
            sentiment=sentiment,
            urgency=urgency,
            extracted_entities=extracted_entities,
            requires_tool=requires_tool,
            suggested_tool=suggested_tool,
            suggested_reply=suggested_reply,
        )

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
    ) -> str:
        ctx_info = f" with info: {context}" if context else ""
        return f"Synthesized response for '{user_message}'{ctx_info}."
