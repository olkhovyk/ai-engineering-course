from datetime import datetime, date, time
from pydantic import BaseModel


class ShiftBase(BaseModel):
    staff_id: int
    shift_date: date
    start_time: time
    end_time: time


class ShiftCreate(ShiftBase):
    created_by: str = "manual"


class ShiftOut(ShiftBase):
    id: int
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
