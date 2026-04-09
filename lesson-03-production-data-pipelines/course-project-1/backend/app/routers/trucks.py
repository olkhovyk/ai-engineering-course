from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.truck import TruckCreate, TruckUpdate, TruckOut
from app.services import truck_service

router = APIRouter(prefix="/trucks", tags=["trucks"])


@router.get("", response_model=list[TruckOut])
async def list_trucks(status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await truck_service.get_trucks(db, status)


@router.get("/{truck_id}", response_model=TruckOut)
async def get_truck(truck_id: int, db: AsyncSession = Depends(get_db)):
    truck = await truck_service.get_truck(db, truck_id)
    if not truck:
        raise HTTPException(404, "Truck not found")
    return truck


@router.post("", response_model=TruckOut, status_code=201)
async def create_truck(data: TruckCreate, db: AsyncSession = Depends(get_db)):
    return await truck_service.create_truck(db, data)


@router.patch("/{truck_id}", response_model=TruckOut)
async def update_truck(truck_id: int, data: TruckUpdate, db: AsyncSession = Depends(get_db)):
    truck = await truck_service.update_truck(db, truck_id, data)
    if not truck:
        raise HTTPException(404, "Truck not found")
    return truck
