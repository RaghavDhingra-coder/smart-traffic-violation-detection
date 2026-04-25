from typing import Optional

from pydantic import BaseModel, validator

try:
    from .challan import ChallanResponse
except ImportError:
    from schemas.challan import ChallanResponse


class DetectRequest(BaseModel):
    frame: str
    source: str = "webcam"

    class Config:
        orm_mode = True


class DetectionItem(BaseModel):
    track_id: Optional[int] = None
    plate: str
    type: str

    @validator("plate")
    def normalize_plate(cls, value: str) -> str:
        plate = value.replace(" ", "").upper()
        if not plate:
            raise ValueError("plate cannot be empty")
        return plate

    @validator("type")
    def normalize_type(cls, value: str) -> str:
        vtype = value.strip().upper()
        if not vtype:
            raise ValueError("type cannot be empty")
        return vtype

    class Config:
        orm_mode = True


class DetectResponse(BaseModel):
    detections: list[DetectionItem]
    stored_challans: list[ChallanResponse]

    class Config:
        orm_mode = True
