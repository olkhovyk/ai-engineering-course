from datetime import datetime, time, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schedule import DeliverySchedule
from app.models.truck import Truck
from app.models.staff import Staff
from app.models.shift import Shift
from app.agents.messages import publish_truck_arrived, publish_manual_trigger
from app.simulation_clock import sim_clock

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/clock")
async def get_clock():
    return {"current_time": sim_clock.now().isoformat()}


@router.post("/clock/set")
async def set_clock(iso_time: str):
    dt = datetime.fromisoformat(iso_time)
    sim_clock.set_time(dt)
    return {"current_time": sim_clock.now().isoformat()}


@router.post("/clock/reset")
async def reset_clock():
    sim_clock.reset()
    return {"current_time": sim_clock.now().isoformat()}


@router.post("/tick")
async def tick(minutes: int = 15, db: AsyncSession = Depends(get_db)):
    new_time = sim_clock.advance(minutes)
    events = []

    # Find trucks that should have arrived by now
    q = select(DeliverySchedule).where(
        and_(
            DeliverySchedule.expected_arrival <= new_time,
            DeliverySchedule.status == "planned",
        )
    )
    result = await db.execute(q)
    newly_arrived = result.scalars().all()

    for entry in newly_arrived:
        entry.actual_arrival = entry.expected_arrival
        entry.status = "arrived"
        truck = await db.get(Truck, entry.truck_id)
        if truck:
            truck.status = "waiting"
        events.append({"type": "truck_arrived", "schedule_id": entry.id, "truck_id": entry.truck_id})

    # Update staff statuses based on shifts
    # Staff whose shift started should be "available"
    active_shifts_q = select(Shift).where(
        and_(
            Shift.shift_date == new_time.date(),
            Shift.start_time <= new_time.time(),
            Shift.end_time > new_time.time(),
        )
    )
    active_result = await db.execute(active_shifts_q)
    active_shifts = active_result.scalars().all()
    active_staff_ids = {s.staff_id for s in active_shifts}

    # Set on-shift staff to "available" (if not already "busy")
    if active_staff_ids:
        await db.execute(
            update(Staff)
            .where(and_(Staff.id.in_(active_staff_ids), Staff.status == "off_duty"))
            .values(status="available")
        )

    # Set staff whose shift ended to "off_duty"
    all_staff_result = await db.execute(select(Staff).where(Staff.status.in_(["available", "on_break"])))
    for s in all_staff_result.scalars().all():
        if s.id not in active_staff_ids:
            s.status = "off_duty"

    await db.commit()

    # Trigger agent processing for arrived trucks
    for event in events:
        await publish_truck_arrived(event["schedule_id"])

    return {
        "current_time": new_time.isoformat(),
        "events": events,
        "staff_on_shift": len(active_staff_ids),
    }


@router.post("/seed")
async def seed_database():
    from app.seed.seed_data import run_seed
    await run_seed()
    return {"ok": True, "message": "Database seeded"}


@router.post("/scenario/{name}")
async def load_scenario(name: str, db: AsyncSession = Depends(get_db)):
    from app.seed.seed_data import load_scenario
    result = await load_scenario(name)
    return result
