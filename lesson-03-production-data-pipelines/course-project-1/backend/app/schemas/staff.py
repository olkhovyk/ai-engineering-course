from datetime import datetime
from pydantic import BaseModel


class StaffBase(BaseModel):
    full_name: str
    role: str
    phone: str | None = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    status: str | None = None
    phone: str | None = None


class StaffOut(StaffBase):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
