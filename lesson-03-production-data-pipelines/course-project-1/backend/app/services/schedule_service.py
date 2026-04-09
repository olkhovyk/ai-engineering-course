from datetime import date, datetime, time, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import DeliverySchedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


async def get_schedules(db: AsyncSession, schedule_date: date | None = None, status: str | None = None) -> list[DeliverySchedule]:
    q = select(DeliverySchedule)
    if schedule_date:
        start = datetime.combine(schedule_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(schedule_date, time.max, tzinfo=timezone.utc)
        q = q.where(and_(DeliverySchedule.expected_arrival >= start, DeliverySchedule.expected_arrival <= end))
    if status:
        q = q.where(DeliverySchedule.status == status)
    q = q.order_by(DeliverySchedule.expected_arrival)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_schedule(db: AsyncSession, schedule_id: int) -> DeliverySchedule | None:
    return await db.get(DeliverySchedule, schedule_id)


async def create_schedule(db: AsyncSession, data: ScheduleCreate) -> DeliverySchedule:
    entry = DeliverySchedule(**data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def update_schedule(db: AsyncSession, schedule_id: int, data: ScheduleUpdate) -> DeliverySchedule | None:
    entry = await db.get(DeliverySchedule, schedule_id)
    if not entry:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(entry, key, val)
    await db.commit()
    await db.refresh(entry)
    return entry


async def mark_arrived(db: AsyncSession, schedule_id: int, arrival_time: datetime) -> DeliverySchedule | None:
    entry = await db.get(DeliverySchedule, schedule_id)
    if not entry:
        return None
    entry.actual_arrival = arrival_time
    entry.status = "arrived"
    await db.commit()
    await db.refresh(entry)
    return entry


async def mark_completed(db: AsyncSession, schedule_id: int) -> DeliverySchedule | None:
    entry = await db.get(DeliverySchedule, schedule_id)
    if not entry:
        return None
    entry.status = "completed"
    await db.commit()
    await db.refresh(entry)
    return entry
