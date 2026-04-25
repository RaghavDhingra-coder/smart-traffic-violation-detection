import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

try:
    from ..models.challan import Challan
    from ..redis_client import redis_client
    from ..schemas.challan import ChallanCreate
except ImportError:
    from models.challan import Challan
    from redis_client import redis_client
    from schemas.challan import ChallanCreate

DEDUP_WINDOW_SECONDS = 10
PLATE_CACHE_TTL_SECONDS = 120


def _serialize_challan(challan: Challan) -> dict[str, Any]:
    return {
        "id": challan.id,
        "plate": challan.plate,
        "violation_type": challan.violation_type,
        "timestamp": challan.timestamp.isoformat(),
        "status": challan.status,
    }


def _normalize_plate(plate: str) -> str:
    return plate.replace(" ", "").upper()


def _normalize_violation_type(violation_type: str) -> str:
    return violation_type.strip().upper()


async def get_challans_by_plate(plate: str, db: Session) -> list[dict[str, Any]]:
    normalized_plate = _normalize_plate(plate)
    cache_key = f"challans:plate:{normalized_plate}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    records = (
        db.query(Challan)
        .filter(Challan.plate == normalized_plate)
        .order_by(Challan.timestamp.desc())
        .all()
    )
    serialized = [_serialize_challan(challan) for challan in records]
    redis_client.setex(cache_key, PLATE_CACHE_TTL_SECONDS, json.dumps(serialized))
    return serialized


async def create_challan(payload: ChallanCreate, db: Session) -> Challan | None:
    normalized_plate = _normalize_plate(payload.plate)
    normalized_type = _normalize_violation_type(payload.violation_type)
    dedupe_key = f"violation:{normalized_plate}:{normalized_type}"

    is_fresh = redis_client.set(
        dedupe_key,
        payload.timestamp.isoformat(),
        ex=DEDUP_WINDOW_SECONDS,
        nx=True,
    )
    if not is_fresh:
        threshold = payload.timestamp - timedelta(seconds=DEDUP_WINDOW_SECONDS)
        return (
            db.query(Challan)
            .filter(
                Challan.plate == normalized_plate,
                Challan.violation_type == normalized_type,
                Challan.timestamp >= threshold,
            )
            .order_by(Challan.timestamp.desc())
            .first()
        )

    challan = Challan(
        plate=normalized_plate,
        violation_type=normalized_type,
        timestamp=payload.timestamp,
        image_url=payload.image_url,
        status="UNPAID",
    )
    db.add(challan)
    db.commit()
    db.refresh(challan)

    redis_client.delete(f"challans:plate:{normalized_plate}")
    redis_client.setex(
        f"challan:recent:{normalized_plate}",
        PLATE_CACHE_TTL_SECONDS,
        json.dumps(_serialize_challan(challan)),
    )
    return challan


async def create_challan_from_detection(
    plate: str,
    violation_type: str,
    db: Session,
    image_url: str | None = None,
) -> Challan | None:
    payload = ChallanCreate(
        plate=plate,
        violation_type=violation_type,
        timestamp=datetime.utcnow(),
        image_url=image_url,
    )
    return await create_challan(payload, db)
