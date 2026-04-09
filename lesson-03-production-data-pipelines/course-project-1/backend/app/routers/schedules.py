from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut
from app.services import schedule_service
from app.simulation_clock import sim_clock

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(schedule_date: date | None = None, status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await schedule_service.get_schedules(db, schedule_date, status)


@router.get("/today", response_model=list[ScheduleOut])
async def today_schedules(db: AsyncSession = Depends(get_db)):
    today = sim_clock.now().date()
    return await schedule_service.get_schedules(db, today)


@router.post("", response_model=ScheduleOut, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await schedule_service.create_schedule(db, data)


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(schedule_id: int, data: ScheduleUpdate, db: AsyncSession = Depends(get_db)):
    entry = await schedule_service.update_schedule(db, schedule_id, data)
    if not entry:
        raise HTTPException(404, "Schedule entry not found")
    return entry


@router.post("/{schedule_id}/arrive", response_model=ScheduleOut)
async def mark_arrived(schedule_id: int, db: AsyncSession = Depends(get_db)):
    now = sim_clock.now()
    entry = await schedule_service.mark_arrived(db, schedule_id, now)
    if not entry:
        raise HTTPException(404, "Schedule entry not found")
    # Trigger agent coordination via Redis (handled in agents module)
    from app.agents.messages import publish_truck_arrived
    await publish_truck_arrived(schedule_id)
    return entry


@router.post("/{schedule_id}/complete", response_model=ScheduleOut)
async def mark_completed(schedule_id: int, db: AsyncSession = Depends(get_db)):
    entry = await schedule_service.mark_completed(db, schedule_id)
    if not entry:
        raise HTTPException(404, "Schedule entry not found")
    from app.agents.messages import publish_unloading_complete
    await publish_unloading_complete(schedule_id)
    return entry
