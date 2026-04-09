from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dock import Dock
from app.schemas.dock import DockCreate


async def get_docks(db: AsyncSession, status: str | None = None) -> list[Dock]:
    q = select(Dock)
    if status:
        q = q.where(Dock.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_dock(db: AsyncSession, dock_id: int) -> Dock | None:
    return await db.get(Dock, dock_id)


async def create_dock(db: AsyncSession, data: DockCreate) -> Dock:
    dock = Dock(**data.model_dump())
    db.add(dock)
    await db.commit()
    await db.refresh(dock)
    return dock


async def update_dock_status(db: AsyncSession, dock_id: int, status: str) -> Dock | None:
    dock = await db.get(Dock, dock_id)
    if not dock:
        return None
    dock.status = status
    await db.commit()
    await db.refresh(dock)
    return dock
