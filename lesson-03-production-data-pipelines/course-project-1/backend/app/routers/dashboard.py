from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.dock import Dock
from app.models.truck import Truck
from app.models.staff import Staff
from app.models.schedule import DeliverySchedule
from app.models.notification import Notification
from app.models.agent_log import AgentLog
from app.schemas.dashboard import DashboardSummary, TimelineEntry
from app.simulation_clock import sim_clock

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    now = sim_clock.now()
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    # Trucks today
    truck_q = select(DeliverySchedule.status, func.count()).where(
        and_(DeliverySchedule.expected_arrival >= today_start, DeliverySchedule.expected_arrival <= today_end)
    ).group_by(DeliverySchedule.status)
    truck_result = await db.execute(truck_q)
    truck_counts = dict(truck_result.all())

    total_trucks = sum(truck_counts.values())
    trucks_waiting = truck_counts.get("arrived", 0)
    trucks_unloading = truck_counts.get("in_progress", 0)
    trucks_completed = truck_counts.get("completed", 0)

    # Docks
    dock_q = select(Dock.status, func.count()).group_by(Dock.status)
    dock_result = await db.execute(dock_q)
    dock_counts = dict(dock_result.all())

    docks_total = sum(dock_counts.values())
    docks_occupied = dock_counts.get("occupied", 0)
    docks_free = dock_counts.get("free", 0)

    # Staff
    staff_q = select(Staff.status, Staff.role, func.count()).group_by(Staff.status, Staff.role)
    staff_result = await db.execute(staff_q)
    staff_rows = staff_result.all()

    staff_available = sum(r[2] for r in staff_rows if r[0] == "available")
    staff_busy = sum(r[2] for r in staff_rows if r[0] == "busy")
    staff_off_duty = sum(r[2] for r in staff_rows if r[0] == "off_duty")
    loaders_available = sum(r[2] for r in staff_rows if r[0] == "available" and r[1] == "loader")
    forklift_available = sum(r[2] for r in staff_rows if r[0] == "available" and r[1] == "forklift_operator")

    # Notifications
    unread_q = select(func.count()).select_from(Notification).where(Notification.is_read == False)
    unread = (await db.execute(unread_q)).scalar() or 0

    # Alerts today
    alerts_q = select(func.count()).select_from(AgentLog).where(
        and_(
            AgentLog.severity.in_(["warning", "critical"]),
            AgentLog.created_at >= today_start,
        )
    )
    alerts = (await db.execute(alerts_q)).scalar() or 0

    return DashboardSummary(
        total_trucks_today=total_trucks,
        trucks_waiting=trucks_waiting,
        trucks_unloading=trucks_unloading,
        trucks_completed=trucks_completed,
        docks_total=docks_total,
        docks_occupied=docks_occupied,
        docks_free=docks_free,
        staff_available=staff_available,
        staff_busy=staff_busy,
        staff_off_duty=staff_off_duty,
        loaders_available=loaders_available,
        forklift_operators_available=forklift_available,
        unread_notifications=unread,
        alerts_today=alerts,
    )


@router.get("/timeline", response_model=list[TimelineEntry])
async def dashboard_timeline(db: AsyncSession = Depends(get_db)):
    now = sim_clock.now()
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    q = (
        select(DeliverySchedule, Truck, Dock)
        .join(Truck, DeliverySchedule.truck_id == Truck.id)
        .outerjoin(Dock, DeliverySchedule.dock_id == Dock.id)
        .where(and_(DeliverySchedule.expected_arrival >= today_start, DeliverySchedule.expected_arrival <= today_end))
        .order_by(DeliverySchedule.expected_arrival)
    )
    result = await db.execute(q)
    rows = result.all()

    return [
        TimelineEntry(
            schedule_id=sched.id,
            truck_license_plate=truck.license_plate,
            expected_arrival=sched.expected_arrival,
            actual_arrival=sched.actual_arrival,
            dock_code=dock.code if dock else None,
            status=sched.status,
            estimated_unload_minutes=sched.estimated_unload_minutes,
        )
        for sched, truck, dock in rows
    ]
