# TODO for detection-schemas: extend payloads with richer evidence metadata, frame indexing, and bounding box schemas.
from pydantic import BaseModel


class ViolationOut(BaseModel):
    type: str
    confidence: float
    plate_number: str | None = None
    annotated_frame_base64: str | None = None

    class Config:
        orm_mode = True


class DetectionResult(BaseModel):
    violations: list[ViolationOut]
    total_frames_processed: int | None = None

    class Config:
        orm_mode = True
