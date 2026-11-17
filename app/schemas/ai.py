from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    ORDER_INQUIRY = "order_inquiry"
    REFUND_REQUEST = "refund_request"
    SUPPORT_TICKET = "support_ticket"
    FAQ_GENERAL = "faq_general"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMClassificationResult(BaseModel):
    """
    Structured output returned by the LLM Intent Classifier.
    """
    intent: IntentCategory = Field(..., description="Primary categorized intent of the customer message.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0.")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description="Customer emotional sentiment.")
    urgency: Urgency = Field(default=Urgency.MEDIUM, description="Urgency level based on customer wording.")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key entities extracted from text (e.g., {'order_id': 'ORD-1042'}).",
    )
    requires_tool: bool = Field(
        default=False,
        description="Whether answering this message requires calling an external tool or database query.",
    )
    suggested_tool: Optional[str] = Field(
        default=None,
        description="Recommended tool name: fetch_order_status, create_support_ticket, issue_refund.",
    )
    suggested_reply: Optional[str] = Field(
        default=None,
        description="Draft customer response synthesized by the model.",
    )
