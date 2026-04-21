# TODO for payment-model: add signature fields, settlement references, and gateway payload retention for audits.
from sqlalchemy import Column, ForeignKey, Integer, String

from database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    challan_id = Column(Integer, ForeignKey("challans.id"), nullable=False)
    razorpay_order_id = Column(String(128), nullable=False)
    status = Column(String(32), default="created", nullable=False)
