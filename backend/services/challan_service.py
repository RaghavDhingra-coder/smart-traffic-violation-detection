# TODO for challan-service: add duplicate suppression, officer workflow hooks, and asynchronous notifications.
from sqlalchemy.orm import Session

from models.challan import Challan
from schemas.challan import ChallanCreate
from services.vehicle_service import get_vehicle_by_plate

VIOLATION_AMOUNTS = {
    "no_helmet": 500,
    "trippling": 1000,
    "overspeeding": 2000,
    "traffic_light_jump": 1000,
    "no_parking": 500,
    "no_number_plate": 5000,
}


async def get_challans_by_plate(plate: str, db: Session) -> list[Challan]:
    normalized_plate = plate.replace(" ", "").upper()
    return db.query(Challan).filter(Challan.plate == normalized_plate).order_by(Challan.timestamp.desc()).all()


async def create_challan(payload: ChallanCreate, db: Session) -> Challan:
    normalized_plate = payload.plate.replace(" ", "").upper()
    await get_vehicle_by_plate(normalized_plate, db)

    amount = VIOLATION_AMOUNTS.get(payload.violation_type)
    if amount is None:
        raise ValueError(f"Unsupported violation type: {payload.violation_type}")

    challan = Challan(
        plate=normalized_plate,
        violation_type=payload.violation_type,
        amount=amount,
        status="pending",
        image_path=payload.image_path,
    )
    db.add(challan)
    db.commit()
    db.refresh(challan)
    return challan


async def update_challan_status(challan_id: int, status: str, db: Session) -> Challan | None:
    challan = db.query(Challan).filter(Challan.id == challan_id).first()
    if not challan:
        return None

    challan.status = status
    db.add(challan)
    db.commit()
    db.refresh(challan)
    return challan
