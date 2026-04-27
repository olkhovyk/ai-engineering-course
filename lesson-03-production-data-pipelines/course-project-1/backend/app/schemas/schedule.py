from datetime import datetime
from pydantic import BaseModel


class ScheduleBase(BaseModel):
    truck_id: int
    expected_arrival: datetime
    estimated_unload_minutes: int = 60


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    expected_arrival: datetime | None = None
    estimated_unload_minutes: int | None = None
    status: str | None = None


class ScheduleOut(ScheduleBase):
    id: int
    actual_arrival: datetime | None
    dock_id: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
