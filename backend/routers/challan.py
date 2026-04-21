# TODO for challan-router: add officer authorization, filtering, pagination, and dismissal audit flows.
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.challan import ChallanCreate, ChallanOut, ChallanStatusUpdate
from services.challan_service import create_challan, get_challans_by_plate, update_challan_status
from services.vehicle_service import get_vehicle_by_plate

router = APIRouter(tags=["challan"])


@router.get("/challan/{plate}", response_model=list[ChallanOut])
async def get_challan_by_plate(plate: str, db: Session = Depends(get_db)):
    try:
        return await get_challans_by_plate(plate, db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch challans: {exc}") from exc


@router.post("/challan", response_model=ChallanOut)
async def create_new_challan(payload: ChallanCreate, db: Session = Depends(get_db)):
    try:
        return await create_challan(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to create challan: {exc}") from exc


@router.patch("/challan/{challan_id}/status", response_model=ChallanOut)
async def patch_challan_status(challan_id: int, payload: ChallanStatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in {"pending", "paid", "dismissed"}:
        raise HTTPException(status_code=400, detail="Invalid challan status")

    try:
        challan = await update_challan_status(challan_id, payload.status, db)
        if not challan:
            raise HTTPException(status_code=404, detail="Challan not found")
        return challan
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to update challan: {exc}") from exc


@router.get("/vehicle/{plate}")
async def get_vehicle_details(plate: str, db: Session = Depends(get_db)):
    try:
        vehicle = await get_vehicle_by_plate(plate, db)
        challans = await get_challans_by_plate(plate, db)
        return {"vehicle": vehicle, "challans": [ChallanOut.from_orm(item).dict() for item in challans]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch vehicle details: {exc}") from exc
