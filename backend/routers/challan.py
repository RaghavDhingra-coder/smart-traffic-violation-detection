from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..schemas.challan import ChallanCreate, ChallanResponse
    from ..services.challan_service import create_challan, get_challans_by_plate
except ImportError:
    from database import get_db
    from schemas.challan import ChallanCreate, ChallanResponse
    from services.challan_service import create_challan, get_challans_by_plate

router = APIRouter(tags=["challan"])


@router.post("/challan", response_model=ChallanResponse)
async def create_new_challan(payload: ChallanCreate, db: Session = Depends(get_db)):
    try:
        challan = await create_challan(payload, db)
        return challan
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to create challan: {exc}") from exc


@router.get("/challan/{plate}", response_model=list[ChallanResponse])
async def get_challan_by_plate(plate: str, db: Session = Depends(get_db)):
    try:
        return await get_challans_by_plate(plate, db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch challans: {exc}") from exc
