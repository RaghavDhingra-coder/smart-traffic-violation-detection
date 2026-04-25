from datetime import datetime
from typing import Optional

from pydantic import BaseModel, validator


class ChallanCreate(BaseModel):
    plate: str
    violation_type: str
    timestamp: datetime
    image_url: Optional[str] = None

    @validator("plate")
    def normalize_plate(cls, value: str) -> str:
        plate = value.replace(" ", "").upper()
        if not plate:
            raise ValueError("plate cannot be empty")
        return plate

    @validator("violation_type")
    def normalize_violation_type(cls, value: str) -> str:
        vtype = value.strip().upper()
        if not vtype:
            raise ValueError("violation_type cannot be empty")
        return vtype

    class Config:
        orm_mode = True


class ChallanResponse(BaseModel):
    id: int
    plate: str
    violation_type: str
    timestamp: datetime
    status: str

    class Config:
        orm_mode = True
