"""Challan schemas with comprehensive validation rules for evidence, officer actions, and dismissal reasons."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class ChallanCreate(BaseModel):
    """Schema for creating a new challan with validation."""

    plate: str = Field(..., min_length=8, max_length=12, example="DL01AB1234")
    violation_type: str = Field(
        ...,
        example="OVER_SPEED",
        description="Type of violation (e.g., OVER_SPEED, NO_HELMET, TRIPPLING, TRAFFIC_LIGHT_JUMP, NO_PARKING, NO_NUMBER_PLATE)",
    )
    image_path: Optional[str] = Field(None, description="Path to evidence image")
    officer_id: Optional[str] = Field(None, description="Badge ID of issuing officer")
    location: Optional[str] = Field(None, description="Location where violation occurred")

    @validator("plate")
    def validate_plate_format(cls, v):
        """Ensure plate follows Indian vehicle number format."""
        import re

        if not re.match(r"^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$", v):
            raise ValueError("Invalid Indian vehicle registration number format")
        return v

    @validator("violation_type")
    def validate_violation_type(cls, v):
        """Ensure violation type is one of the allowed types."""
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

    class Config:
        orm_mode = True


class ChallanStatusUpdate(BaseModel):
    """Schema for updating challan status with validation."""

    status: str = Field(
        ...,
        description="Status: pending, approved, paid, dismissed, appealed",
    )
    dismissal_reason: Optional[str] = Field(
        None,
        description="Reason for dismissal if applicable (e.g., INSUFFICIENT_EVIDENCE, PROCEDURAL_ERROR, OWNER_CONSENT)",
    )
    appeal_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notes for appeal review",
    )

    @validator("status")
    def validate_status(cls, v):
        """Ensure status is valid."""
        allowed_statuses = {"pending", "approved", "paid", "dismissed", "appealed"}
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v

    @validator("dismissal_reason")
    def validate_dismissal_reason(cls, v, values):
        """Ensure dismissal reason is provided if status is dismissed."""
        if values.get("status") == "dismissed" and not v:
            raise ValueError("Dismissal reason required when dismissing a challan")
        return v

    class Config:
        orm_mode = True


class OfficerAction(BaseModel):
    """Schema for officer actions on challan."""

    officer_id: str = Field(..., description="Badge ID of officer")
    action: str = Field(..., description="Action type: REVIEWED, APPROVED, REJECTED, DISMISSED")
    notes: Optional[str] = Field(None, max_length=500, description="Officer notes")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator("action")
    def validate_action(cls, v):
        """Ensure action is valid."""
        allowed_actions = {"REVIEWED", "APPROVED", "REJECTED", "DISMISSED"}
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return v

    class Config:
        orm_mode = True


class EvidenceMetadata(BaseModel):
    """Schema for evidence-related metadata."""

    image_path: str = Field(..., description="Path to evidence image")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence of detection (0-1)")
    frame_index: Optional[int] = Field(None, description="Frame index in video evidence")
    bounding_box: Optional[dict] = Field(
        None,
        description="Bounding box coordinates {x1, y1, x2, y2}",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


class ChallanOut(BaseModel):
    """Complete challan response schema."""

    id: int
    plate: str
    violation_type: str
    amount: int
    status: str
    timestamp: datetime
    image_path: Optional[str] = None
    officer_id: Optional[str] = None
    location: Optional[str] = None
    dismissal_reason: Optional[str] = None
    appeal_notes: Optional[str] = None
    evidence: Optional[EvidenceMetadata] = None
    officer_actions: Optional[list] = None

    class Config:
        orm_mode = True


class ChallanListResponse(BaseModel):
    """Response for list of challans with pagination."""

    total: int
    count: int
    page: int
    per_page: int
    data: list[ChallanOut]
