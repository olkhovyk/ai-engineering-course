from datetime import datetime
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_trucks_today: int
    trucks_waiting: int
    trucks_unloading: int
    trucks_completed: int
    docks_total: int
    docks_occupied: int
    docks_free: int
    staff_available: int
    staff_busy: int
    staff_off_duty: int
    loaders_available: int
    forklift_operators_available: int
    unread_notifications: int
    alerts_today: int


class TimelineEntry(BaseModel):
    schedule_id: int
    truck_license_plate: str
    expected_arrival: datetime
    actual_arrival: datetime | None
    dock_code: str | None
    status: str
    estimated_unload_minutes: int
