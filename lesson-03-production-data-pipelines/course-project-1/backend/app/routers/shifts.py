from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.shift import ShiftCreate, ShiftOut
from app.services import shift_service
from app.simulation_clock import sim_clock

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("", response_model=list[ShiftOut])
async def list_shifts(shift_date: date | None = None, staff_id: int | None = None, db: AsyncSession = Depends(get_db)):
    return await shift_service.get_shifts(db, shift_date, staff_id)


@router.get("/active", response_model=list[ShiftOut])
async def active_shifts(db: AsyncSession = Depends(get_db)):
    now = sim_clock.now()
    return await shift_service.get_active_shifts(db, now.date(), now.time())


@router.post("", response_model=ShiftOut, status_code=201)
async def create_shift(data: ShiftCreate, db: AsyncSession = Depends(get_db)):
    return await shift_service.create_shift(db, data)


@router.delete("/{shift_id}", status_code=204)
async def delete_shift(shift_id: int, db: AsyncSession = Depends(get_db)):
    if not await shift_service.delete_shift(db, shift_id):
        raise HTTPException(404, "Shift not found")
