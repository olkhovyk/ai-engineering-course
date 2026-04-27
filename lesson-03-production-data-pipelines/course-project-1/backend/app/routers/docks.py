from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dock import DockCreate, DockStatusUpdate, DockOut
from app.services import dock_service

router = APIRouter(prefix="/docks", tags=["docks"])


@router.get("", response_model=list[DockOut])
async def list_docks(status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await dock_service.get_docks(db, status)


@router.get("/{dock_id}", response_model=DockOut)
async def get_dock(dock_id: int, db: AsyncSession = Depends(get_db)):
    dock = await dock_service.get_dock(db, dock_id)
    if not dock:
        raise HTTPException(404, "Dock not found")
    return dock


@router.post("", response_model=DockOut, status_code=201)
async def create_dock(data: DockCreate, db: AsyncSession = Depends(get_db)):
    return await dock_service.create_dock(db, data)


@router.patch("/{dock_id}/status", response_model=DockOut)
async def update_dock_status(dock_id: int, data: DockStatusUpdate, db: AsyncSession = Depends(get_db)):
    dock = await dock_service.update_dock_status(db, dock_id, data.status)
    if not dock:
        raise HTTPException(404, "Dock not found")
    return dock
