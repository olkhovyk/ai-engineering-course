from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.staff import StaffCreate, StaffUpdate, StaffOut
from app.services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=list[StaffOut])
async def list_staff(role: str | None = None, status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await staff_service.get_staff_list(db, role, status)


@router.get("/{staff_id}", response_model=StaffOut)
async def get_staff(staff_id: int, db: AsyncSession = Depends(get_db)):
    member = await staff_service.get_staff(db, staff_id)
    if not member:
        raise HTTPException(404, "Staff not found")
    return member


@router.post("", response_model=StaffOut, status_code=201)
async def create_staff(data: StaffCreate, db: AsyncSession = Depends(get_db)):
    return await staff_service.create_staff(db, data)


@router.patch("/{staff_id}", response_model=StaffOut)
async def update_staff(staff_id: int, data: StaffUpdate, db: AsyncSession = Depends(get_db)):
    member = await staff_service.update_staff(db, staff_id, data)
    if not member:
        raise HTTPException(404, "Staff not found")
    return member
