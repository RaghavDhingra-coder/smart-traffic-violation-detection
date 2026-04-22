"""Payment schemas with gateway verification, receipts, and webhook support."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class PaymentCreate(BaseModel):
    """Schema for creating a payment order."""

    challan_id: int = Field(..., description="Challan ID to pay for")
    amount: int = Field(..., gt=0, description="Amount in paise (smallest currency unit)")
    currency: str = Field(default="INR", description="Currency code")
    payment_method: Optional[str] = Field(None, description="Payment method: card, netbanking, upi, wallet")

    @validator("currency")
    def validate_currency(cls, v):
        """Ensure currency is valid."""
        allowed_currencies = {"INR", "USD", "EUR"}
        if v not in allowed_currencies:
            raise ValueError(f"Currency must be one of {allowed_currencies}")
        return v

    class Config:
        orm_mode = True


class PaymentVerifyRequest(BaseModel):
    """Schema for payment verification with gateway response."""

    challan_id: int = Field(..., description="Challan ID")
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature for verification")

    class Config:
        orm_mode = True


class PaymentReceipt(BaseModel):
    """Schema for payment receipt."""

    receipt_id: str = Field(..., description="Unique receipt identifier")
    challan_id: int
    amount: int
    currency: str = "INR"
    payment_id: str
    order_id: str
    status: str
    payment_timestamp: datetime
    receipt_url: Optional[str] = Field(None, description="URL to download receipt")

    class Config:
        orm_mode = True


class WebhookPayload(BaseModel):
    """Schema for payment gateway webhook payload."""

    event: str = Field(..., description="Webhook event type: payment.authorized, payment.failed, payment.captured")
    payment_id: str = Field(..., description="Payment ID from gateway")
    order_id: str = Field(..., description="Order ID from gateway")
    status: str = Field(..., description="Payment status from gateway")
    amount: int
    currency: str = "INR"
    receipt: Optional[str] = None
    error_code: Optional[str] = Field(None, description="Error code if payment failed")
    error_description: Optional[str] = Field(None, description="Error description if payment failed")
    timestamp: int = Field(..., description="Unix timestamp of event")

    @validator("event")
    def validate_event(cls, v):
        """Ensure event type is valid."""
        allowed_events = {"payment.authorized", "payment.failed", "payment.captured", "payment.refunded"}
        if v not in allowed_events:
            raise ValueError(f"Event must be one of {allowed_events}")
        return v

    class Config:
        orm_mode = True


class PaymentOut(BaseModel):
    """Complete payment response schema."""

    id: Optional[int] = None
    challan_id: int
    razorpay_order_id: str
    status: str
    amount: Optional[int] = None
    currency: Optional[str] = "INR"
    key_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    receipt: Optional[PaymentReceipt] = None

    class Config:
        orm_mode = True


class PaymentListResponse(BaseModel):
    """Response for list of payments with pagination."""

    total: int
    count: int
    page: int
    per_page: int
    data: list[PaymentOut]

    class Config:
        orm_mode = True


class RefundRequest(BaseModel):
    """Schema for requesting a refund."""

    payment_id: str = Field(..., description="Payment ID to refund")
    reason: str = Field(..., max_length=500, description="Reason for refund")
    challan_id: int = Field(..., description="Associated challan ID")

    @validator("reason")
    def validate_reason_length(cls, v):
        """Ensure reason is provided."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Refund reason must be at least 10 characters")
        return v

    class Config:
        orm_mode = True
