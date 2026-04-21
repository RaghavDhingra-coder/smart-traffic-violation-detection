# TODO for payment-schemas: support gateway verification payloads, receipts, and webhook-specific contracts.
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    challan_id: int
    amount: int
    currency: str = "INR"

    class Config:
        orm_mode = True


class PaymentVerifyRequest(BaseModel):
    challan_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

    class Config:
        orm_mode = True


class PaymentOut(BaseModel):
    id: int | None = None
    challan_id: int
    razorpay_order_id: str
    status: str
    amount: int | None = None
    currency: str | None = None
    key_id: str | None = None

    class Config:
        orm_mode = True
