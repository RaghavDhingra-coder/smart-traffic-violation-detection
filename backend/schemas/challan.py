# TODO for challan-schemas: add validation rules for evidence, officer actions, and dismissal reasons.
from datetime import datetime

from pydantic import BaseModel


class ChallanCreate(BaseModel):
    plate: str
    violation_type: str
    image_path: str | None = None

    class Config:
        orm_mode = True


class ChallanStatusUpdate(BaseModel):
    status: str

    class Config:
        orm_mode = True


class ChallanOut(BaseModel):
    id: int
    plate: str
    violation_type: str
    amount: int
    status: str
    timestamp: datetime
    image_path: str | None = None

    class Config:
        orm_mode = True
