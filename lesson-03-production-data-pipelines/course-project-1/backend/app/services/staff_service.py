from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffUpdate


async def get_staff_list(db: AsyncSession, role: str | None = None, status: str | None = None) -> list[Staff]:
    q = select(Staff)
    if role:
        q = q.where(Staff.role == role)
    if status:
        q = q.where(Staff.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_staff(db: AsyncSession, staff_id: int) -> Staff | None:
    return await db.get(Staff, staff_id)


async def create_staff(db: AsyncSession, data: StaffCreate) -> Staff:
    member = Staff(**data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_staff(db: AsyncSession, staff_id: int, data: StaffUpdate) -> Staff | None:
    member = await db.get(Staff, staff_id)
    if not member:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(member, key, val)
    await db.commit()
    await db.refresh(member)
    return member
