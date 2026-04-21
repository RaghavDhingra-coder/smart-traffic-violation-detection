# TODO for payment-service: replace the stubbed order generation with real Razorpay SDK integration and signature verification.
import uuid

from sqlalchemy.orm import Session

from config import settings
from models.payment import Payment
from schemas.payment import PaymentCreate, PaymentOut, PaymentVerifyRequest


async def create_payment_order(payload: PaymentCreate, db: Session) -> PaymentOut:
    razorpay_order_id = f"order_{uuid.uuid4().hex[:16]}"

    # STUB: replace with real implementation using the Razorpay SDK and server-side order creation.
    payment = Payment(
        challan_id=payload.challan_id,
        razorpay_order_id=razorpay_order_id,
        status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PaymentOut(
        id=payment.id,
        challan_id=payment.challan_id,
        razorpay_order_id=payment.razorpay_order_id,
        status=payment.status,
        amount=payload.amount,
        currency=payload.currency,
        key_id=settings.razorpay_key_id,
    )


async def verify_payment(payload: PaymentVerifyRequest, db: Session) -> PaymentOut | None:
    payment = db.query(Payment).filter(Payment.razorpay_order_id == payload.razorpay_order_id).first()
    if not payment:
        return None

    # STUB: replace with real implementation by validating Razorpay signatures server-side.
    payment.status = "paid"
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PaymentOut(
        id=payment.id,
        challan_id=payment.challan_id,
        razorpay_order_id=payment.razorpay_order_id,
        status=payment.status,
    )
