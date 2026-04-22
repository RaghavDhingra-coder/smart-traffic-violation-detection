# TODO for detection-schemas: extend payloads with richer evidence metadata, frame indexing, and bounding box schemas.
from typing import Optional

from pydantic import BaseModel


class ViolationOut(BaseModel):
    type: str
    confidence: float
    plate_number: Optional[str] = None
    annotated_frame_base64: Optional[str] = None

    class Config:
        orm_mode = True


class DetectionResult(BaseModel):
    violations: list[ViolationOut]
    total_frames_processed: Optional[int] = None

    class Config:
        orm_mode = True
