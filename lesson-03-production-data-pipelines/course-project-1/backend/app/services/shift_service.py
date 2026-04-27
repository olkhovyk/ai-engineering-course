from datetime import date, time

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shift import Shift
from app.schemas.shift import ShiftCreate


async def get_shifts(db: AsyncSession, shift_date: date | None = None, staff_id: int | None = None) -> list[Shift]:
    q = select(Shift)
    if shift_date:
        q = q.where(Shift.shift_date == shift_date)
    if staff_id:
        q = q.where(Shift.staff_id == staff_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_active_shifts(db: AsyncSession, current_date: date, current_time: time) -> list[Shift]:
    q = select(Shift).where(
        and_(
            Shift.shift_date == current_date,
            Shift.start_time <= current_time,
            Shift.end_time > current_time,
        )
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_shift(db: AsyncSession, data: ShiftCreate) -> Shift:
    shift = Shift(**data.model_dump())
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


async def delete_shift(db: AsyncSession, shift_id: int) -> bool:
    shift = await db.get(Shift, shift_id)
    if not shift:
        return False
    await db.delete(shift)
    await db.commit()
    return True
