# TODO for payment-router: add webhook support, retry-safe verification, and secure signature validation.
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.payment import PaymentCreate, PaymentOut, PaymentVerifyRequest
from services.payment_service import create_payment_order, verify_payment

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/create-order", response_model=PaymentOut)
async def create_order(payload: PaymentCreate, db: Session = Depends(get_db)):
    try:
        return await create_payment_order(payload, db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {exc}") from exc


@router.post("/verify", response_model=PaymentOut)
async def verify_order(payload: PaymentVerifyRequest, db: Session = Depends(get_db)):
    try:
        payment = await verify_payment(payload, db)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment order not found")
        return payment
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to verify payment: {exc}") from exc
