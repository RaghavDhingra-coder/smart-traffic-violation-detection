from fastapi import APIRouter

try:
    from ..schemas.violation import ViolationCreate, ViolationCreateResponse, ViolationRecord
    from ..services.violation_service import (
        fetch_all_violations,
        fetch_vehicle_violations,
        insert_violation,
        is_stolen_vehicle,
        send_over_speed_alert,
    )
except ImportError:
    from schemas.violation import ViolationCreate, ViolationCreateResponse, ViolationRecord
    from services.violation_service import (
        fetch_all_violations,
        fetch_vehicle_violations,
        insert_violation,
        is_stolen_vehicle,
        send_over_speed_alert,
    )

router = APIRouter(tags=["violations"])


@router.post("/violation", response_model=ViolationCreateResponse)
def create_violation(payload: ViolationCreate):
    violation = insert_violation(payload)
    message = "violation stored successfully"

    if payload.type.upper() == "OVER_SPEED":
        send_over_speed_alert(payload.plate)

    if is_stolen_vehicle(payload.plate):
        message = "stolen vehicle detected"

    return ViolationCreateResponse(
        message=message,
        violation=ViolationRecord(**violation),
    )


@router.get("/violations", response_model=list[ViolationRecord])
def get_violations():
    return [ViolationRecord(**violation) for violation in fetch_all_violations()]


@router.get("/vehicle/{plate}", response_model=list[ViolationRecord])
def get_vehicle_violations(plate: str):
    return [ViolationRecord(**violation) for violation in fetch_vehicle_violations(plate)]
