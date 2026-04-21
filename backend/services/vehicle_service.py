# TODO for vehicle-lookup-service: replace the stubbed registry flow with real Vaahan integration and richer cache invalidation.
import json

from redis import Redis
from sqlalchemy.orm import Session

from config import settings
from models.vehicle import Vehicle

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_vehicle_by_plate(plate: str, db: Session) -> dict:
    normalized_plate = plate.replace(" ", "").upper()
    cache_key = f"vehicle:{normalized_plate}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    vehicle = db.query(Vehicle).filter(Vehicle.plate == normalized_plate).first()
    if vehicle:
        data = {
            "plate": vehicle.plate,
            "owner_name": vehicle.owner_name,
            "owner_contact": vehicle.owner_contact,
            "vehicle_type": vehicle.vehicle_type,
            "registration_state": vehicle.registration_state,
        }
        redis_client.setex(cache_key, 3600, json.dumps(data))
        return data

    # STUB: replace with real implementation by calling the Vaahan API using settings.vaahan_api_key.
    mock_data = {
        "plate": normalized_plate,
        "owner_name": "Test Owner",
        "owner_contact": "+91-9000000000",
        "vehicle_type": "motorcycle",
        "registration_state": "KA",
    }

    db_vehicle = Vehicle(
        plate=mock_data["plate"],
        owner_name=mock_data["owner_name"],
        owner_contact=mock_data["owner_contact"],
        vehicle_type=mock_data["vehicle_type"],
        registration_state=mock_data["registration_state"],
    )
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)

    redis_client.setex(cache_key, 3600, json.dumps(mock_data))
    return mock_data
