from datetime import datetime
from pydantic import BaseModel


class AssignmentBase(BaseModel):
    schedule_entry_id: int
    staff_id: int
    dock_id: int
    role_needed: str


class AssignmentCreate(AssignmentBase):
    assigned_by: str = "manual"


class AssignmentOut(AssignmentBase):
    id: int
    assigned_at: datetime
    completed_at: datetime | None
    assigned_by: str

    model_config = {"from_attributes": True}
