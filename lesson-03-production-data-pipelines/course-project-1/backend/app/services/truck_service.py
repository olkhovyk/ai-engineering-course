from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.truck import Truck
from app.schemas.truck import TruckCreate, TruckUpdate


async def get_trucks(db: AsyncSession, status: str | None = None) -> list[Truck]:
    q = select(Truck)
    if status:
        q = q.where(Truck.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_truck(db: AsyncSession, truck_id: int) -> Truck | None:
    return await db.get(Truck, truck_id)


async def create_truck(db: AsyncSession, data: TruckCreate) -> Truck:
    truck = Truck(**data.model_dump())
    db.add(truck)
    await db.commit()
    await db.refresh(truck)
    return truck


async def update_truck(db: AsyncSession, truck_id: int, data: TruckUpdate) -> Truck | None:
    truck = await db.get(Truck, truck_id)
    if not truck:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(truck, key, val)
    await db.commit()
    await db.refresh(truck)
    return truck
