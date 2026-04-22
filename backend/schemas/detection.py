"""Detection schemas with richer evidence metadata, frame indexing, and bounding box support."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class BoundingBox(BaseModel):
    """Schema for bounding box coordinates."""

    x1: float = Field(..., ge=0, description="Top-left X coordinate")
    y1: float = Field(..., ge=0, description="Top-left Y coordinate")
    x2: float = Field(..., ge=0, description="Bottom-right X coordinate")
    y2: float = Field(..., ge=0, description="Bottom-right Y coordinate")

    @validator("x2")
    def validate_x_coords(cls, v, values):
        """Ensure x2 > x1."""
        if "x1" in values and v <= values["x1"]:
            raise ValueError("x2 must be greater than x1")
        return v

    @validator("y2")
    def validate_y_coords(cls, v, values):
        """Ensure y2 > y1."""
        if "y1" in values and v <= values["y1"]:
            raise ValueError("y2 must be greater than y1")
        return v

    class Config:
        orm_mode = True


class FrameMetadata(BaseModel):
    """Schema for frame-specific metadata."""

    frame_index: int = Field(..., ge=0, description="Frame index in video sequence")
    timestamp_ms: float = Field(..., ge=0, description="Timestamp in milliseconds")
    bounding_box: Optional[BoundingBox] = None

    class Config:
        orm_mode = True


class ViolationOut(BaseModel):
    """Enhanced violation schema with evidence metadata."""

    type: str = Field(
        ...,
        example="OVER_SPEED",
        description="Violation type detected",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of detection (0-1)",
    )
    plate_number: Optional[str] = Field(None, example="DL01AB1234", description="Detected plate number")
    annotated_frame_base64: Optional[str] = Field(None, description="Base64 encoded annotated frame image")
    frame_metadata: Optional[FrameMetadata] = None
    evidence_quality: Optional[str] = Field(
        None,
        description="Quality rating: excellent, good, fair, poor",
    )

    @validator("type")
    def validate_type(cls, v):
        """Ensure violation type is valid."""
        allowed_types = {
            "OVER_SPEED",
            "NO_HELMET",
            "TRIPPLING",
            "TRAFFIC_LIGHT_JUMP",
            "NO_PARKING",
            "NO_NUMBER_PLATE",
            "RASH_DRIVING",
            "WRONG_WAY",
        }
        if v not in allowed_types:
            raise ValueError(f"Violation type must be one of {allowed_types}")
        return v

    @validator("evidence_quality")
    def validate_evidence_quality(cls, v):
        """Ensure evidence quality is valid."""
        if v is not None:
            allowed_qualities = {"excellent", "good", "fair", "poor"}
            if v not in allowed_qualities:
                raise ValueError(f"Evidence quality must be one of {allowed_qualities}")
        return v

    class Config:
        orm_mode = True


class DetectionResult(BaseModel):
    """Complete detection result with metadata."""

    violations: list[ViolationOut]
    total_frames_processed: Optional[int] = None
    video_duration_ms: Optional[float] = None
    detection_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    model_version: Optional[str] = None

    class Config:
        orm_mode = True


class BatchDetectionResult(BaseModel):
    """Response for batch detection results."""

    batch_id: str = Field(..., description="Unique batch identifier")
    total_detections: int
    detections: list[DetectionResult]
    processing_start: datetime
    processing_end: datetime

    class Config:
        orm_mode = True
