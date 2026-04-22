from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ViolationCreate(BaseModel):
    type: str = Field(..., example="OVER_SPEED")
    plate: str = Field(..., example="DL01AB1234")
    timestamp: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)
    image_url: Optional[str] = Field(default=None, example="https://example.com/violation.jpg")
    location: Optional[str] = Field(default=None, example="Ring Road, Delhi")

    @classmethod
    def from_detection(cls, violation_out, location: Optional[str] = None):
        plate_number = (getattr(violation_out, "plate_number", None) or "").strip()
        if not plate_number:
            return None

        return cls(
            type=violation_out.type,
            plate=plate_number,
            timestamp=datetime.utcnow(),
            confidence=violation_out.confidence,
            image_url=getattr(violation_out, "annotated_frame_base64", None),
            location=location,
        )


class ViolationRecord(ViolationCreate):
    id: int


class ViolationCreateResponse(BaseModel):
    message: str
    violation: ViolationRecord
