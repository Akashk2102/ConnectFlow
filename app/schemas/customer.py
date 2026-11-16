import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# E.164 phone format regex (e.g. +14155552671)
E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class CustomerBase(BaseModel):
    phone_number: str = Field(
        ...,
        examples=["+14155552671"],
        description="Customer phone number in international E.164 format (+[country code][number]).",
    )
    name: Optional[str] = Field(None, examples=["Alice Smith"], max_length=120)
    email: Optional[EmailStr] = Field(None, examples=["alice@example.com"])
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        examples=[{"tier": "vip", "city": "San Francisco"}],
        description="Arbitrary customer metadata / CRM attributes.",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_e164_format(cls, value: str) -> str:
        clean_val = value.strip().replace(" ", "").replace("-", "")
        if not E164_REGEX.match(clean_val):
            raise ValueError(
                f"Phone number '{value}' is invalid. Must follow E.164 format (e.g., +14155552671)."
            )
        return clean_val


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    email: Optional[EmailStr] = None
    custom_metadata: Optional[Dict[str, Any]] = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
