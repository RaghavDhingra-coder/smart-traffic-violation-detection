# TODO for challan-model: add geolocation, officer metadata, evidence references, and payment reconciliation fields.
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from database import Base


class Challan(Base):
    __tablename__ = "challans"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(32), index=True, nullable=False)
    violation_type = Column(String(64), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    image_path = Column(String(255), nullable=True)
