from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.assignment import AssignmentCreate, AssignmentOut
from app.services import assignment_service

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentOut])
async def list_assignments(schedule_entry_id: int | None = None, db: AsyncSession = Depends(get_db)):
    return await assignment_service.get_assignments(db, schedule_entry_id)


@router.get("/active", response_model=list[AssignmentOut])
async def active_assignments(db: AsyncSession = Depends(get_db)):
    return await assignment_service.get_active_assignments(db)


@router.post("", response_model=AssignmentOut, status_code=201)
async def create_assignment(data: AssignmentCreate, db: AsyncSession = Depends(get_db)):
    return await assignment_service.create_assignment(db, data)
