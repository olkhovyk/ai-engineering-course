from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.schemas.assignment import AssignmentCreate


async def get_assignments(db: AsyncSession, schedule_entry_id: int | None = None) -> list[Assignment]:
    q = select(Assignment)
    if schedule_entry_id:
        q = q.where(Assignment.schedule_entry_id == schedule_entry_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_active_assignments(db: AsyncSession) -> list[Assignment]:
    q = select(Assignment).where(Assignment.completed_at.is_(None))
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_assignment(db: AsyncSession, data: AssignmentCreate) -> Assignment:
    assignment = Assignment(**data.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment
